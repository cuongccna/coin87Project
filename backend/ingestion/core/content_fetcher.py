from __future__ import annotations

import logging
import time
import random
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import httpx
from readability import Document
from bs4 import BeautifulSoup
import json
from urllib.parse import urlparse, urlunparse

from ingestion.core.fetch_context import FetchContext

logger = logging.getLogger("coin87.ingestion.content")


# Domain-specific extraction rules
DOMAIN_RULES = {
    "coindesk.com": {
        "main_selector": "article .article-body",
        "remove_selectors": [".ad-container", ".related-articles", ".author-bio"],
    },
    "theblock.co": {
        "main_selector": "article .article-content",
        "remove_selectors": [".premium-content-gate", ".newsletter-signup"],
    },
    "cointelegraph.com": {
        "main_selector": "article .post-content",
        "remove_selectors": [".promo-block", ".tags-list"],
    },
    "decrypt.co": {
        "main_selector": "article .post-content",
        "remove_selectors": [".newsletter-form"],
    },
}

# Fetch rate limiting (global)
_fetch_timestamps: list[float] = []
_max_fetches_per_minute = 20  # Conservative limit




def _apply_random_delay():
    """Random delay 3-15s giữa các detailed fetch."""
    delay = random.uniform(3.0, 15.0)
    logger.debug(f"Applying random delay: {delay:.1f}s")
    time.sleep(delay)


def _check_rate_limit() -> bool:
    """Check xem có vượt rate limit không."""
    global _fetch_timestamps
    now = time.time()
    
    # Loại bỏ timestamps cũ hơn 1 phút
    _fetch_timestamps = [ts for ts in _fetch_timestamps if now - ts < 60]
    
    if len(_fetch_timestamps) >= _max_fetches_per_minute:
        logger.warning(f"Rate limit reached: {len(_fetch_timestamps)} fetches in last minute")
        return False
    
    _fetch_timestamps.append(now)
    return True


def _try_head_request(url: str, timeout: float = 5.0) -> Tuple[bool, Optional[Dict[str, str]]]:
    """
    HEAD request pre-check để validate URL trước khi GET full content.
    
    Returns:
        (should_proceed, headers_dict)
    """
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.head(url)
            
            if resp.status_code >= 400:
                logger.info(f"HEAD check failed: {resp.status_code} for {url}")
                return False, None
            
            headers = dict(resp.headers)
            content_type = headers.get("content-type", "").lower()
            content_length = headers.get("content-length")
            
            # Validate content-type
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                logger.info(f"HEAD check: non-HTML content-type: {content_type}")
                return False, headers
            
            # Validate content-length (nếu có)
            if content_length:
                try:
                    length = int(content_length)
                    if length < 500:  # Quá nhỏ
                        logger.info(f"HEAD check: content too small ({length} bytes)")
                        return False, headers
                    if length > 10_000_000:  # > 10MB
                        logger.warning(f"HEAD check: content very large ({length} bytes)")
                        # Không reject, nhưng warn
                except ValueError:
                    pass
            
            return True, headers
            
    except Exception as e:
        logger.debug(f"HEAD request failed: {e}")
        # Không reject nếu HEAD fail - có thể server không support HEAD
        return True, None


def _extract_with_domain_rules(html: str, url: str) -> Tuple[str, str]:
    """Extract sử dụng domain-specific rules nếu có."""
    domain = urlparse(url).netloc.replace("www.", "")
    
    rules = DOMAIN_RULES.get(domain)
    if not rules:
        # Fallback to generic extraction
        return extract_text_from_html(html)
    
    try:
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove unwanted elements
        for selector in rules.get("remove_selectors", []):
            for elem in soup.select(selector):
                elem.decompose()
        
        # Extract main content
        main_selector = rules["main_selector"]
        main_content = soup.select_one(main_selector)
        
        if main_content:
            text = main_content.get_text(separator="\n\n").strip()
            excerpt = "\n".join(text.splitlines()[:5]).strip()
            return text, excerpt
        else:
            # Fallback if selector không match
            logger.debug(f"Domain rule selector not found: {main_selector}")
            return extract_text_from_html(html)
            
    except Exception as e:
        logger.warning(f"Domain-specific extraction failed: {e}")
        return extract_text_from_html(html)


def _try_amp_fallback(url: str, ctx: FetchContext, source_key: str) -> Tuple[Optional[str], Optional[Dict]]:
    """Thử lấy AMP version nếu site chặn normal fetch."""
    parsed = urlparse(url)
    
    # Try AMP subdomain
    if not parsed.netloc.startswith("amp."):
        amp_netloc = "amp." + parsed.netloc
        amp_url = parsed._replace(netloc=amp_netloc)
        amp_url_str = urlunparse(amp_url)
        
        logger.info(f"Trying AMP fallback: {amp_url_str}")
        status, html, meta = ctx.fetch_text(
            source=type("X", (), {"key": source_key, "url": amp_url_str, "rate_limit_seconds": 60, "proxy": True})  # type: ignore
        )
        
        if status and 200 <= status < 300 and html:
            return html, meta
    
    # Try /amp path suffix
    if not url.endswith("/amp") and not url.endswith("/amp/"):
        amp_path_url = url.rstrip("/") + "/amp"
        logger.info(f"Trying AMP path fallback: {amp_path_url}")
        status, html, meta = ctx.fetch_text(
            source=type("X", (), {"key": source_key, "url": amp_path_url, "rate_limit_seconds": 60, "proxy": True})  # type: ignore
        )
        
        if status and 200 <= status < 300 and html:
            return html, meta
    
    return None, None


def extract_text_from_html(html: str) -> Tuple[str, str]:
    """Return (text, excerpt) extracted from HTML. Uses readability with BS fallback."""
    try:
        doc = Document(html)
        content_html = doc.summary()
        soup = BeautifulSoup(content_html, "html.parser")
        text = soup.get_text(separator="\n\n").strip()
        excerpt = "\n".join(text.splitlines()[:5]).strip()
        return text, excerpt
    except Exception:
        # Fallback full page
        soup = BeautifulSoup(html, "html.parser")
        # Try to pick main tag
        main = soup.find("main") or soup.find("article") or soup
        text = main.get_text(separator="\n\n").strip()
        excerpt = "\n".join(text.splitlines()[:5]).strip()
        return text, excerpt


def fetch_and_extract(url: str, ctx: FetchContext, source_key: str) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
    """Fetch a URL via provided FetchContext and return (html, text, meta).

    Meta contains: proxy_used, status, duration_seconds, fetched_at, fallback (if used)
    
    Implements:
    - Rate limiting (max fetches/minute)
    - Random delay between fetches
    - HEAD pre-check
    - Domain-specific extraction
    - AMP fallback for blocked sites
    """
    # 1. Rate limit check
    if not _check_rate_limit():
        return None, None, {
            "error": "rate_limit_exceeded",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    
    # 2. Random delay (human-like behavior)
    _apply_random_delay()
    
    # 3. HEAD pre-check (optional, không block nếu fail)
    should_proceed, head_headers = _try_head_request(url)
    if not should_proceed:
        logger.info(f"Skipping fetch due to HEAD check: {url}")
        return None, None, {
            "error": "head_check_failed",
            "head_headers": head_headers,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    
    # 4. Actual fetch
    start = time.time()
    status, html, meta = ctx.fetch_text(source=type("X", (), {"key": source_key, "url": url, "rate_limit_seconds": 60, "proxy": True}))  # type: ignore
    duration = time.time() - start
    
    meta_out: Dict[str, Any] = {
        "proxy_used": meta.get("proxy", False),
        "status": status,
        "duration_seconds": duration,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    if status and status >= 200 and status < 300 and html:
        try:
            # 5. Extract with domain rules
            text, excerpt = _extract_with_domain_rules(html, url)

            # 6. Heuristic fallback for Reddit (existing logic)
            if "reddit" in url and ("New to Reddit?" in (html or "") or (not text) or len(text) < 200):
                logger.info("Detected reddit gate or short extract; attempting old.reddit / .json fallbacks for %s", url)
                parsed = urlparse(url)
                
                # Try old.reddit.com
                old_netloc = "old.reddit.com"
                old_parsed = parsed._replace(netloc=old_netloc)
                old_url = urlunparse(old_parsed)
                s2, html2, meta2 = ctx.fetch_text(source=type("X", (), {"key": source_key, "url": old_url, "rate_limit_seconds": 60, "proxy": True}))  # type: ignore
                if s2 and 200 <= s2 < 300 and html2:
                    try:
                        text2, excerpt2 = extract_text_from_html(html2)
                        if text2 and len(text2) > len(text):
                            return html2, text2, {**meta_out, "excerpt": excerpt2, "fallback": "old.reddit.com"}
                    except Exception:
                        pass

                # Try .json endpoint for reddit posts
                json_url = url if url.endswith('.json') else url.rstrip('/') + '.json'
                s3, html3, meta3 = ctx.fetch_text(source=type("X", (), {"key": source_key, "url": json_url, "rate_limit_seconds": 60, "proxy": True}))  # type: ignore
                if s3 and 200 <= s3 < 300 and html3:
                    try:
                        parsed_json = json.loads(html3)
                        body_text = None
                        if isinstance(parsed_json, list) and parsed_json:
                            post = parsed_json[0]
                            body_text = post.get("data", {}).get("children", [])[0].get("data", {}).get("selftext")
                            title = post.get("data", {}).get("children", [])[0].get("data", {}).get("title")
                            combined = (title or "") + "\n\n" + (body_text or "")
                            if combined.strip():
                                return html3, combined.strip(), {**meta_out, "excerpt": "\n".join(combined.splitlines()[:5]), "fallback": "reddit.json"}
                        elif isinstance(parsed_json, dict):
                            body_text = parsed_json.get("selftext") or parsed_json.get("body")
                            if body_text:
                                return html3, body_text, {**meta_out, "excerpt": "\n".join(body_text.splitlines()[:5]), "fallback": "reddit.json"}
                    except Exception:
                        logger.debug("Failed to parse reddit JSON fallback for %s", url)

            # 7. Check if extraction quá ngắn (có thể bị gate/paywall)
            if len(text) < 200:
                logger.info(f"Extracted text very short ({len(text)} chars), trying AMP fallback")
                amp_html, amp_meta = _try_amp_fallback(url, ctx, source_key)
                if amp_html:
                    try:
                        amp_text, amp_excerpt = extract_text_from_html(amp_html)
                        if len(amp_text) > len(text):
                            return amp_html, amp_text, {**meta_out, "excerpt": amp_excerpt, "fallback": "amp"}
                    except Exception:
                        pass

            return html, text, {**meta_out, "excerpt": excerpt}
        except Exception as e:
            logger.exception("Extraction failed: %s", e)
            return html, None, meta_out

    return None, None, meta_out

