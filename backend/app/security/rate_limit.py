"""Institutional rate limiting (conservative, cadence-aligned).

Design:
- Fixed window per hour, per token (fingerprint).
- No per-second burst logic; institutions should not need it.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from fastapi import HTTPException, status


class RateLimitExceeded(HTTPException):
    pass


@dataclass(slots=True)
class _Window:
    start_hour: int
    count: int


class InMemoryHourlyRateLimiter:
    """Simple per-process limiter.

    Operational safeguard:
    - Intended for single-instance / single-worker deployments typical for early
      institutional pilots.
    - If you run multiple workers, limits become per-worker; enforce single worker
      at deployment for strict guarantees.
    """

    def __init__(self, *, limit_per_hour: int) -> None:
        self._limit = limit_per_hour
        self._windows: dict[str, _Window] = {}

    def check(self, key: str) -> None:
        now = int(time.time())
        hour = now // 3600
        w = self._windows.get(key)
        if w is None or w.start_hour != hour:
            w = _Window(start_hour=hour, count=0)
            self._windows[key] = w
        w.count += 1
        if w.count > self._limit:
            raise RateLimitExceeded(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please reduce request cadence.",
            )


def get_hourly_limit() -> int:
    v = os.environ.get("C87_RATE_LIMIT_PER_HOUR", "100")
    try:
        n = int(v)
    except ValueError as e:
        raise RuntimeError("Invalid C87_RATE_LIMIT_PER_HOUR; must be integer.") from e
    if n <= 0:
        raise RuntimeError("C87_RATE_LIMIT_PER_HOUR must be > 0.")
    return n


LIMITER = InMemoryHourlyRateLimiter(limit_per_hour=get_hourly_limit())

