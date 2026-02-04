from __future__ import annotations

"""FetchContext for Job A (human-like, low-risk fetching).

Trust & governance intent:
- No aggressive concurrency.
- Rate-limit per source.
- Random jitter (1–5s by default) to avoid bot-like patterns.
- Optional proxy support (configurable per source).
- Never retry aggressively after 403/429.
- Adaptive backoff based on source health.
"""

import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
import logging

import httpx
from ingestion.core.state import PostgresStateStore, FetchOutcome, SourceState
from ingestion.core.identity import COMMON_HEADERS_CHROME_WIN, COMMON_HEADERS_FIREFOX_MAC

logger = logging.getLogger("coin87.ingestion.fetch")

DEFAULT_USER_AGENTS: list[str] = [
    # Conservative UAs (no headless).
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36",
]


@dataclass(frozen=True, slots=True)
class SourceConfig:
    key: str
    enabled: bool
    type: str
    url: str
    rate_limit_seconds: int
    proxy: bool
    priority: str  # low|medium|high
    tier: int = 3  # Default tier
    name: str | None = None


class FetchContext:
    """Holds runtime controls for fetch behavior within a single Job A run."""

    def __init__(
        self,
        *,
        user_agents: Optional[list[str]] = None,
        jitter_seconds_min: float = 1.0,
        jitter_seconds_max: float = 5.0,
        timeout_seconds: float = 15.0,
        enable_adaptive_backoff: bool = True,
    ) -> None:
        self._user_agents = user_agents or DEFAULT_USER_AGENTS
        self._jmin = float(jitter_seconds_min)
        self._jmax = float(jitter_seconds_max)
        self._timeout = float(timeout_seconds)
        self._enable_adaptive_backoff = enable_adaptive_backoff
        self._store = PostgresStateStore()
        
        # In-memory memory of what we fetched in THIS process run 
        # (to prevent double fetch if bug exists, though Store handles across runs)
        self._session_fetched: set[str] = set()

    def choose_headers(self) -> dict[str, str]:
        return random.choice([COMMON_HEADERS_CHROME_WIN, COMMON_HEADERS_FIREFOX_MAC]).copy()

    def jitter_sleep(self) -> None:
        delay = random.uniform(self._jmin, self._jmax)
        time.sleep(delay)

    def proxy_url_for(self, source: SourceConfig) -> Optional[str]:
        """Get proxy URL for source với tier-based selection.
        
        Tier 1: Residential proxy bắt buộc (high-value sources)
        Tier 2: Datacenter proxy preferred
        Tier 3+: Direct connection (low-risk sources)
        """
        if not source.proxy:
            return None
        
        proxy_env = os.environ.get("C87_PROXY_URL", "") or ""
        proxy_env = proxy_env.strip()

        # FIX: defensive cleanup for malformed env values that include the key itself
        # e.g. someone exported: "C87_PROXY_URL=C87_PROXY_URL=socks5://..."
        if proxy_env.startswith("C87_PROXY_URL="):
            proxy_env = proxy_env.split("=", 1)[1].strip()

        # Remove surrounding quotes if present
        if (proxy_env.startswith('"') and proxy_env.endswith('"')) or (
            proxy_env.startswith("'") and proxy_env.endswith("'")
        ):
            proxy_env = proxy_env[1:-1].strip()

        if not proxy_env:
            # Nếu không có proxy config nhưng source yêu cầu proxy (tier 1)
            if source.tier == 1:
                logger.warning(f"Tier 1 source {source.key} requires proxy but C87_PROXY_URL not set")
            return None
        
        # Parse proxy pools (format: "socks5://residential1,socks5://residential2|http://dc1,http://dc2")
        # Separator: | giữa residential và datacenter pools
        # Separator: , giữa proxies trong cùng pool
        parts = proxy_env.split("|")
        
        residential_proxies = []
        datacenter_proxies = []
        
        if len(parts) >= 1:
            residential_proxies = [p.strip() for p in parts[0].split(",") if p.strip()]
        if len(parts) >= 2:
            datacenter_proxies = [p.strip() for p in parts[1].split(",") if p.strip()]
        
        # Tier-based selection
        if source.tier == 1:
            # Tier 1: MUST use residential
            if not residential_proxies:
                logger.warning(f"Tier 1 source {source.key} needs residential proxy but none configured")
                # Fallback to any proxy available
                all_proxies = residential_proxies + datacenter_proxies
                if not all_proxies:
                    return None
                proxies = all_proxies
            else:
                proxies = residential_proxies
        elif source.tier == 2:
            # Tier 2: Prefer datacenter, fallback to residential
            if datacenter_proxies:
                proxies = datacenter_proxies
            elif residential_proxies:
                proxies = residential_proxies
            else:
                return None
        else:
            # Tier 3+: Direct preferred (proxy optional)
            # Chỉ dùng proxy nếu source.proxy = true explicitly
            all_proxies = datacenter_proxies + residential_proxies
            if not all_proxies:
                return None
            proxies = all_proxies
        
        # Round-robin rotation
        if not hasattr(self, '_proxy_rotation_index'):
            self._proxy_rotation_index = 0
        
        self._proxy_rotation_index = (self._proxy_rotation_index + 1) % len(proxies)
        selected = proxies[self._proxy_rotation_index]
        
        logger.debug(f"Selected proxy for {source.key} (tier {source.tier}): {selected}")
        return selected

    def fetch_text(self, *, source: SourceConfig) -> tuple[int | None, str | None, dict[str, Any]]:
        """Fetch URL content (text) for a source with conservative behavior.

        Returns: (status_code, text, meta)
        - Never raises; caller must treat None as failure.
        - meta is safe for logging (no raw content).
        - Implements adaptive backoff on 403/429 via PostgresStateStore.
        """
        # Load persistent state
        state = self._store.load_state(source.key)
        
        # 1. Check Circuit Breaker / Rate Limit
        if self._enable_adaptive_backoff and not state.can_fetch():
             return None, None, {
                "source_key": source.key,
                "skipped": True,
                "reason": "circuit_open_or_cooldown",
                "next_allowed": state.next_allowed_at.isoformat() if state.next_allowed_at else None,
            }

        # 2. Check in-process duplicate
        if source.key in self._session_fetched:
             return None, None, {"source_key": source.key, "skipped": True, "reason": "already_fetched_in_session"}

        self.jitter_sleep()

        headers = self.choose_headers()
        
        # Conditional Fetch
        if state.etag:
            headers["If-None-Match"] = state.etag
        if state.last_modified:
            headers["If-Modified-Since"] = state.last_modified

        proxy_url = self.proxy_url_for(source)
        proxies = None
        if proxy_url:
            # Normalize common proxy schemes to what httpx expects.
            # httpx may not accept 'socks5h://' string in some environments; convert to 'socks5://'.
            if proxy_url.startswith("socks5h://"):
                proxy_url = "socks5://" + proxy_url[len("socks5h://"):]

            # Handle SOCKS5 vs HTTP proxies
            if proxy_url.startswith("socks5"):
                # httpx-socks requires mounting specific transport or passing proxies dict differently
                # But httpx natively supports 'socks5://' in `proxies` dict if httpx-socks is installed.
                # httpx expects schema keys to be protocols like 'http://' and 'https://',
                # and the value to be the proxy URL.
                proxies = {
                    "http://": proxy_url,
                    "https://": proxy_url,
                }
            else:
                proxies = {"http://": proxy_url, "https://": proxy_url}

            logger.info(f"Connecting to {source.key} via proxy: {proxy_url}")

        meta: dict[str, Any] = {"source_key": source.key, "url": source.url, "proxy": bool(proxy_url)}
        
        outcome = FetchOutcome.TRANSIENT_ERROR
        new_etag = None
        new_last_mod = None
        next_run = None
        
        try:
            try:
                with httpx.Client(
                    timeout=self._timeout,
                    follow_redirects=True,
                    proxies=proxies,
                ) as client:
                    resp = client.get(source.url, headers=headers)
            except (httpx.ProxyError, httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadError, httpx.RemoteProtocolError) as e:
                # Fallback to direct connection if proxy fails
                if proxies:
                    logger.warning(f"Proxy connection failed ({type(e).__name__}: {e}). Falling back to direct connection for {source.key}.")
                    meta["proxy_failed"] = True
                    meta["proxy_error"] = str(e)
                    # Retry without proxies, but handle any failure gracefully
                    try:
                        with httpx.Client(
                            timeout=self._timeout,
                            follow_redirects=True,
                            proxies=None,
                        ) as client:
                            resp = client.get(source.url, headers=headers)
                    except (httpx.ProxyError, httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadError, httpx.RemoteProtocolError) as e2:
                        logger.warning(f"Direct retry after proxy failure also failed ({type(e2).__name__}: {e2}) for {source.key}.")
                        meta["fallback_error"] = str(e2)
                        # Persist transient error state to trigger adaptive backoff
                        try:
                            self._store.update_state(source.key, FetchOutcome.TRANSIENT_ERROR)
                        except Exception:
                            logger.debug("Failed updating state after fallback error", exc_info=True)
                        return None, None, meta
                else:
                    raise e

            self._session_fetched.add(source.key)

            meta["status_code"] = resp.status_code
            
            # Handling status codes
            if resp.status_code == 304:
                outcome = FetchOutcome.SUCCESS
                logger.info(f"Fetch {source.key}: 304 Not Modified.")
                # Update state to maintain last_checked timestamp
                self._store.update_state(source.key, outcome)
                # Content not modified, return validation but no text (adapters handle None text as empty)
                return 304, None, meta

            if resp.status_code in (403, 429):
                outcome = FetchOutcome.SOFT_BLOCK if resp.status_code == 429 else FetchOutcome.HARD_BLOCK
                
                # Try to parse Retry-After header
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    try:
                        seconds = int(retry_after)
                        next_run = datetime.now(timezone.utc) + timedelta(seconds=seconds)
                    except ValueError:
                        pass # Date format not parsed

                logger.warning(f"Fetch {source.key} BLOCKED: Status {resp.status_code}. Outcome: {outcome.name}. Next retry: {next_run}")
                
                # IMPORTANT: Persist state to trigger backoff/cooldown
                self._store.update_state(source.key, outcome, next_run=next_run)

                return resp.status_code, None, meta

            if resp.status_code >= 400:
                outcome = FetchOutcome.TRANSIENT_ERROR
                logger.error(f"Fetch {source.key} FAILED: Status {resp.status_code}. URL: {source.url}")
                self._store.update_state(source.key, outcome)
                return resp.status_code, None, meta

            # SUCCESS 200
            outcome = FetchOutcome.SUCCESS
            new_etag = resp.headers.get("ETag")
            new_last_mod = resp.headers.get("Last-Modified")
            
            # Save success state (includes resetting backoff)
            self._store.update_state(source.key, outcome, etag=new_etag, last_modified=new_last_mod)

            return resp.status_code, resp.text, meta
                
        except Exception as e:
            logger.exception(f"Fetch {source.key} EXCEPTION: {str(e)}")
            self._store.update_state(source.key, FetchOutcome.TRANSIENT_ERROR)
            meta["error_type"] = type(e).__name__
            return None, None, meta

