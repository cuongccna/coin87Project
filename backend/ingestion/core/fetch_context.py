from __future__ import annotations

"""FetchContext for Job A (human-like, low-risk fetching).

Trust & governance intent:
- No aggressive concurrency.
- Rate-limit per source.
- Random jitter (1–5s by default) to avoid bot-like patterns.
- Optional proxy support (configurable per source).
- Never retry aggressively after 403/429.
"""

import os
import random
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx


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
    ) -> None:
        self._user_agents = user_agents or DEFAULT_USER_AGENTS
        self._jmin = float(jitter_seconds_min)
        self._jmax = float(jitter_seconds_max)
        self._timeout = float(timeout_seconds)
        self._last_fetch_epoch_by_source: dict[str, float] = {}

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

    def proxy_url_for(self, source: SourceConfig) -> Optional[str]:
        if not source.proxy:
            return None
        # Operator-provided proxy URL (never hardcode credentials).
        return os.environ.get("C87_PROXY_URL")

    def fetch_text(self, *, source: SourceConfig) -> tuple[int | None, str | None, dict[str, Any]]:
        """Fetch URL content (text) for a source with conservative behavior.

        Returns: (status_code, text, meta)
        - Never raises; caller must treat None as failure.
        - meta is safe for logging (no raw content).
        """
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
        try:
            with httpx.Client(
                timeout=self._timeout,
                follow_redirects=True,
                proxies=proxies,
            ) as client:
                resp = client.get(source.url, headers=headers)
                self.mark_fetched(source)

                meta["status_code"] = resp.status_code

                # No aggressive retries after 403/429 — return failure to caller.
                if resp.status_code in (403, 429):
                    return resp.status_code, None, meta

                if resp.status_code >= 400:
                    return resp.status_code, None, meta

                return resp.status_code, resp.text, meta
        except Exception as e:  # noqa: BLE001
            meta["error_type"] = type(e).__name__
            return None, None, meta

