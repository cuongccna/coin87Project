"""Simple Redis client helper (sync) used for pub/sub and caching."""
import os
from typing import Optional

try:
    import redis
except Exception:  # pragma: no cover - environment may not have redis installed
    redis = None


_client = None


def get_redis() -> Optional[object]:
    global _client
    if _client is not None:
        return _client

    if redis is None:
        return None

    url = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
    _client = redis.from_url(url)
    return _client
