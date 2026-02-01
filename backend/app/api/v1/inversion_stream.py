from __future__ import annotations

import json
import time
from typing import Generator

from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse

from app.services.redis_client import get_redis

router = APIRouter()


def event_stream() -> Generator[bytes, None, None]:
    """Subscribe to Redis channel and yield Server-Sent Events (SSE).

    This is a simple, best-effort implementation using redis-py's pubsub.
    """
    r = get_redis()
    if r is None:
        # No redis available — yield a comment and exit
        yield b": no redis configured\n\n"
        return

    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe("inversion:updates")

    try:
        # initial ping
        yield b": connected\n\n"
        while True:
            message = pubsub.get_message(timeout=10)
            if message is None:
                # heartbeat to keep connection alive
                yield b": heartbeat\n\n"
                time.sleep(1)
                continue

            data = message.get("data")
            if isinstance(data, bytes):
                try:
                    text = data.decode("utf-8")
                except Exception:
                    text = str(data)
            else:
                text = str(data)

            # format as SSE
            sse = f"data: {text}\n\n"
            yield sse.encode("utf-8")
    finally:
        try:
            pubsub.close()
        except Exception:
            pass


@router.get("/inversion-stream")
def inversion_stream() -> StreamingResponse:
    return StreamingResponse(event_stream(), media_type="text/event-stream")
