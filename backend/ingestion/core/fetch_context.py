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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import httpx


DEFAULT_USER_AGENTS: list[str] = [
    # Conservative UAs (no headless).
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36",
]


@dataclass
class SourceHealth:
    """Track health metrics per source for adaptive backoff."""
    consecutive_failures: int = 0
    last_success_epoch: float | None = None
    last_failure_epoch: float | None = None
    backoff_until_epoch: float | None = None
    total_403_429: int = 0
    
    def should_skip(self) -> bool:
        """Check if source should be skipped due to backoff."""
        if self.backoff_until_epoch is None:
            return False
        return time.time() < self.backoff_until_epoch
    
    def calculate_backoff_seconds(self) -> float:
        """Exponential backoff: 2^failures * base (capped at 1 hour)."""
        base = 60.0  # 1 minute base
        backoff = min(base * (2 ** self.consecutive_failures), 3600.0)
        return backoff
    
    def record_success(self) -> None:
        """Reset failure counters on success."""
        self.consecutive_failures = 0
        self.last_success_epoch = time.time()
        self.backoff_until_epoch = None
    
    def record_failure(self, is_rate_limit: bool = False) -> None:
        """Increment failure counter and set backoff."""
        self.consecutive_failures += 1
        self.last_failure_epoch = time.time()
        if is_rate_limit:
            self.total_403_429 += 1
        backoff_seconds = self.calculate_backoff_seconds()
        self.backoff_until_epoch = time.time() + backoff_seconds


@dataclass(frozen=True, slots=True)
class SourceConfig:
    key: str
    enabled: bool
    type: str
    url: str
    rate_limit_seconds: int
    proxy: bool
    priority: str  # low|medium|high
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
        self._last_fetch_epoch_by_source: dict[str, float] = {}
        self._health_by_source: dict[str, SourceHealth] = {}
        self._proxy_rotation_index: int = 0

    def choose_user_agent(self) -> str:
        return random.choice(self._user_agents)

    def jitter_sleep(self) -> None:
        delay = random.uniform(self._jmin, self._jmax)
        time.sleep(delay)

    def rate_limit_sleep_if_needed(self, source: SourceConfig) -> None:
        last = self._last_fetch_epoch_by_source.get(source.key)
        if last is None:
            return
        elapsed = time.time() - last
        remaining = float(source.rate_limit_seconds) - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def mark_fetched(self, source: SourceConfig) -> None:
        self._last_fetch_epoch_by_source[source.key] = time.time()

    def get_health(self, source: SourceConfig) -> SourceHealth:
        """Get or create health tracker for source."""
        if source.key not in self._health_by_source:
            self._health_by_source[source.key] = SourceHealth()
        return self._health_by_source[source.key]

    def should_skip_source(self, source: SourceConfig) -> bool:
        """Check if source should be skipped due to health backoff."""
        if not self._enable_adaptive_backoff:
            return False
        health = self.get_health(source)
        return health.should_skip()

    def proxy_url_for(self, source: SourceConfig) -> Optional[str]:
        """Get proxy URL for source with sticky rotation strategy.
        
        Sticky strategy: use same proxy for a source until it fails,
        then rotate. This reduces fingerprint changes and mimics human behavior.
        """
        if not source.proxy:
            return None
        
        # Check for multiple proxies (comma-separated)
        proxy_env = os.environ.get("C87_PROXY_URL", "")
        if not proxy_env:
            return None
        
        proxies = [p.strip() for p in proxy_env.split(",") if p.strip()]
        if not proxies:
            return None
        
        if len(proxies) == 1:
            return proxies[0]
        
        # Sticky: use health-based index for rotation
        health = self.get_health(source)
        index = health.total_403_429 % len(proxies)
        return proxies[index]

    def fetch_text(self, *, source: SourceConfig) -> tuple[int | None, str | None, dict[str, Any]]:
        """Fetch URL content (text) for a source with conservative behavior.

        Returns: (status_code, text, meta)
        - Never raises; caller must treat None as failure.
        - meta is safe for logging (no raw content).
        - Implements adaptive backoff on 403/429.
        """
        # Check health-based backoff
        if self.should_skip_source(source):
            health = self.get_health(source)
            return None, None, {
                "source_key": source.key,
                "skipped": True,
                "reason": "backoff",
                "backoff_until": health.backoff_until_epoch,
            }

        self.rate_limit_sleep_if_needed(source)
        self.jitter_sleep()

        headers = {
            "User-Agent": self.choose_user_agent(),
            "Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.1",
        }

        proxy_url = self.proxy_url_for(source)
        proxies = None
        if proxy_url:
            proxies = {"http://": proxy_url, "https://": proxy_url}

        meta: dict[str, Any] = {"source_key": source.key, "url": source.url, "proxy": bool(proxy_url)}
        health = self.get_health(source)
        
        try:
            with httpx.Client(
                timeout=self._timeout,
                follow_redirects=True,
                proxies=proxies,
            ) as client:
                resp = client.get(source.url, headers=headers)
                self.mark_fetched(source)

                meta["status_code"] = resp.status_code

                # Handle rate limiting with adaptive backoff
                if resp.status_code in (403, 429):
                    health.record_failure(is_rate_limit=True)
                    meta["backoff_seconds"] = health.calculate_backoff_seconds()
                    return resp.status_code, None, meta

                if resp.status_code >= 400:
                    health.record_failure(is_rate_limit=False)
                    return resp.status_code, None, meta

                # Success: reset health counters
                health.record_success()
                return resp.status_code, resp.text, meta
                
        except Exception as e:  # noqa: BLE001
            meta["error_type"] = type(e).__name__
            health.record_failure(is_rate_limit=False)
            return None, None, meta

