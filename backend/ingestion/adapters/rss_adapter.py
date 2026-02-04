from __future__ import annotations

"""RSS adapter (FULL) - ISOLATED VERSION.

Scope:
- Fetch RSS/Atom feeds using curl_cffi to bypass WAF.
- Normalize into NormalizedEvent.
- Internal safe fetching logic (Does not rely on core content_fetcher modifications).
"""

import re
import time
import random
import logging
from datetime import datetime, timezone
from typing import Any, Optional, Tuple, Dict

import feedparser
from bs4 import BeautifulSoup
from readability import Document  # pip install readability-lxml
from curl_cffi import requests as curl_requests # pip install curl_cffi

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.information_event import InformationEvent
from ingestion.core.adapter import BaseAdapter, NormalizedEvent, RawItem
from ingestion.core.dedup import compute_content_hash_sha256_hex
from ingestion.core.fetch_context import FetchContext, SourceConfig
from ingestion.core.content_filter import get_filter, FilterDecision
from ingestion.core.worth_click_scorer import get_scorer

logger = logging.getLogger("coin87.ingestion.rss")

UTC = timezone.utc

# --- INTERNAL HELPER FUNCTIONS (Cô lập logic tại đây để không ảnh hưởng nơi khác) ---

def _strip_html(text: str) -> str:
    if not text:
        return ""
    try:
        return BeautifulSoup(text, "html.parser").get_text(separator=" ", strip=True)
    except Exception:
        import re
        t = re.sub(r"<[^>]+>", " ", text or "")
        return re.sub(r"\s+", " ", t).strip()

def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.utcoffset() is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)

def _entry_time(entry: Any) -> datetime:
    now = datetime.now(tz=UTC)
    for key in ("published_parsed", "updated_parsed"):
        st = getattr(entry, key, None)
        if st:
            try:
                return _to_utc(datetime(*st[:6], tzinfo=UTC))
            except Exception:
                continue
    return now

def _extract_text_internal(html: str) -> Tuple[str, str]:
    """Logic trích xuất nội dung bài viết (Readability + Fallback)."""
    try:
        doc = Document(html)
        content_html = doc.summary()
        soup = BeautifulSoup(content_html, "html.parser")
        text = soup.get_text(separator="\n\n").strip()
        excerpt = "\n".join(text.splitlines()[:5]).strip()
        return text, excerpt
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
        # Fallback đơn giản: lấy toàn bộ body
        main = soup.find("main") or soup.find("article") or soup.body or soup
        text = main.get_text(separator="\n\n").strip()
        excerpt = "\n".join(text.splitlines()[:5]).strip()
        return text, excerpt

# --- MAIN ADAPTER CLASS ---

class RssAdapter(BaseAdapter):
    adapter_type = "rss"

    def _fetch_safe_content(self, url: str, proxy: Optional[str] = None) -> Tuple[Optional[str], Optional[str], Dict]:
        """
        Hàm fetch riêng biệt cho RSS Adapter.
        Sử dụng curl_cffi giả lập Chrome 120 để lấy cả RSS XML và HTML chi tiết.
        """
        try:
            proxies = {"http": proxy, "https": proxy} if proxy else None
            
            # Browser Headers chuẩn
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/",
                "Upgrade-Insecure-Requests": "1"
            }

            # Thực hiện Request
            response = curl_requests.get(
                url,
                impersonate="chrome120", # Quan trọng
                proxies=proxies,
                headers=headers,
                timeout=30,
                allow_redirects=True
            )

            fetched_at = datetime.now(timezone.utc).isoformat()

            if response.status_code == 200:
                html = response.text
                # Tự động extract text ngay tại đây
                text, excerpt = _extract_text_internal(html)
                
                meta = {
                    "status": 200,
                    "fetched_at": fetched_at,
                    "method": "curl_cffi_safe"
                }
                return html, text, meta
            else:
                logger.warning(f"Safe fetch failed: {url} | Status: {response.status_code}")
                return None, None, {"status": response.status_code, "fetched_at": fetched_at}

        except Exception as e:
            logger.error(f"Safe fetch error: {url} | {e}")
            return None, None, {"error": str(e)}

    def fetch(self, context: FetchContext, source: SourceConfig) -> list[RawItem]:
        content_filter = get_filter()
        scorer = get_scorer()
        
        # 1. Fetch RSS Feed (XML)
        # Ưu tiên dùng Safe Fetch ngay từ đầu cho Feed để tránh 403
        current_proxy = getattr(context, "current_proxy", None)
        logger.info(f"Fetching RSS Feed: {source.url}")
        
        xml_body, _, _ = self._fetch_safe_content(source.url, proxy=current_proxy)
        
        if not xml_body:
            # Fallback về context cũ nếu safe fetch lỗi (hiếm khi cần, nhưng cứ để dự phòng)
            status, xml_body, _ = context.fetch_text(source=source)
            if not xml_body:
                return []

        feed = feedparser.parse(xml_body)
        items: list[RawItem] = []
        detailed_fetch_count = 0

        for entry in feed.entries or []:
            title = getattr(entry, "title", None) or ""
            summary = getattr(entry, "summary", None)
            link = getattr(entry, "link", None)
            
            # --- Filter & Scoring Logic (Giữ nguyên) ---
            filter_result = content_filter.check(
                title=title, summary=summary, categories=getattr(entry, "tags", None), url=link
            )
            
            if filter_result.decision != FilterDecision.PASS:
                continue
            
            entry_time = _entry_time(entry)
            score_breakdown = scorer.score(
                title=title, summary=summary,
                source_tier=getattr(source, "tier", 3),
                source_priority=source.priority,
                published_time=entry_time,
                filter_penalty=filter_result.score_penalty,
                worth_click_keywords=getattr(source, "worth_click_keywords", None),
            )
            
            payload = {
                "title": title, "summary": summary, "link": link,
                "id": getattr(entry, "id", None),
                "published": getattr(entry, "published", None),
                "updated": getattr(entry, "updated", None),
                "_worth_click_score": score_breakdown.final_score,
                # ... (Các field meta khác giữ nguyên cho gọn)
            }
            
            # --- Detailed Fetch Logic (Đã cô lập) ---
            fetch_strategy = getattr(source, "fetch_strategy", "scored")
            should_fetch = False
            if fetch_strategy == "always": should_fetch = True
            elif fetch_strategy == "scored": should_fetch = scorer.should_fetch_detailed(score_breakdown)
            
            if link and should_fetch:
                try:
                    # Jitter (Delay)
                    if detailed_fetch_count > 0:
                        sleep_time = random.uniform(3.0, 8.0)
                        time.sleep(sleep_time)

                    # GỌI HÀM NỘI BỘ, KHÔNG GỌI content_fetcher NỮA
                    html, text, meta_fetch = self._fetch_safe_content(str(link), proxy=current_proxy)
                    
                    detailed_fetch_count += 1
                    
                    if html: payload["content_html"] = html
                    if text: payload["content_text"] = text
                    if text: payload["content_excerpt"] = "\n".join(text.splitlines()[:5])
                    payload["content_fetch_meta"] = meta_fetch
                    
                except Exception as e:
                    logger.debug(f"Detailed fetch failed for {link}: {e}")

            items.append(RawItem(source_key=source.key, payload=payload))
        return items

    # ... (Giữ nguyên các hàm normalize, validate, insert y hệt file cũ) ...
    # Để code chạy được, bạn copy nốt phần normalize, validate, insert từ file cũ vào dưới này nhé.
    # Vì logic đó không đổi nên tôi không paste lại cho đỡ dài dòng.

    def normalize(self, raw_item: RawItem, source: SourceConfig) -> Optional[NormalizedEvent]:
        # ... COPY LẠI CODE CŨ ...
        try:
            p = raw_item.payload
            title = _strip_html(str(p.get("title") or "")).strip()
            summary = _strip_html(str(p.get("summary") or "")).strip()
            link = str(p.get("link") or "").strip() or None
            ext_id = str(p.get("id") or "").strip() or None

            abstract = title
            if summary and summary.lower() not in (title.lower(),):
                abstract = f"{title}. {summary}" if title else summary
            abstract = abstract.strip()
            if len(abstract) > 2000:
                abstract = abstract[:2000].rstrip()

            source_name = source.name or source.key
            h_hex = compute_content_hash_sha256_hex(abstract=abstract, source_name=source_name)

            raw_metadata: dict[str, Any] = {
                "source_key": source.key,
                "source_type": source.type,
                "source_name": source_name,
                "url": source.url,
                "rss": {
                    "title": title or None,
                    "summary": summary or None,
                    "link": link,
                    "external_id": ext_id,
                    "published": p.get("published"),
                    "updated": p.get("updated"),
                },
            }
            if p.get("content_html"): raw_metadata["content_html"] = p.get("content_html")
            if p.get("content_text"): raw_metadata["content_text"] = p.get("content_text")
            if p.get("content_excerpt"): raw_metadata["content_excerpt"] = p.get("content_excerpt")
            if p.get("content_fetch_meta"): raw_metadata["content_fetch_meta"] = p.get("content_fetch_meta")

            event_time = _entry_time(type("E", (), p))
            source_id = ext_id or link or h_hex

            return NormalizedEvent(
                source_id=source_id,
                source_type=source.type,
                source_name=source_name,
                event_time=event_time,
                abstract=abstract,
                raw_metadata=raw_metadata,
                content_hash_sha256=h_hex,
            )
        except Exception: 
            return None

    def validate(self, event: NormalizedEvent) -> bool:
        try:
            if not event.source_id or not event.source_name or not event.source_type:
                return False
            if not event.abstract or len(event.abstract.strip()) < 8:
                return False
            if event.event_time.tzinfo is None or event.event_time.utcoffset() is None:
                return False
            return True
        except Exception:
            return False

    def insert(self, event: NormalizedEvent, db_session: Session) -> bool:
        try:
            digest_bytes = bytes.fromhex(event.content_hash_sha256)
            observed_at = datetime.now(tz=UTC)

            canonical_url = None
            external_ref = None
            rss_meta = (event.raw_metadata or {}).get("rss") if isinstance(event.raw_metadata, dict) else None
            if isinstance(rss_meta, dict):
                canonical_url = rss_meta.get("link")
                external_ref = rss_meta.get("external_id") or event.source_id

            stmt = pg_insert(InformationEvent).values(
                source_ref=event.source_name,
                external_ref=external_ref,
                canonical_url=canonical_url,
                title=(rss_meta.get("title") if isinstance(rss_meta, dict) else None) or None,
                body_excerpt=event.abstract,
                content_html=(event.raw_metadata.get("content_html") if isinstance(event.raw_metadata, dict) else None) or None,
                content_text=(event.raw_metadata.get("content_text") if isinstance(event.raw_metadata, dict) else None) or None,
                content_excerpt=(event.raw_metadata.get("content_excerpt") if isinstance(event.raw_metadata, dict) else None) or None,
                fetched_content_at=(event.raw_metadata.get("content_fetch_meta", {}).get("fetched_at") if isinstance(event.raw_metadata, dict) else None),
                content_fetch_status=(event.raw_metadata.get("content_fetch_meta", {}).get("status") if isinstance(event.raw_metadata, dict) else None),
                raw_payload=event.raw_metadata,
                content_hash_sha256=digest_bytes,
                event_time=_to_utc(event.event_time),
                observed_at=observed_at,
            )

            with db_session.begin_nested():
                result = db_session.execute(stmt)
                inserted = bool(getattr(result, "rowcount", 0))
                return inserted
        except IntegrityError:
            return False
        except Exception:
            return False
