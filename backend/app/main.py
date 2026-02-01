"""FastAPI application (institutional, read-only).

Operational hardening goals:
- Deterministic, low-noise responses
- Strict authentication + role-based authorization
- Conservative rate limiting
- Request-id propagation and structured access logs
- Safe failure modes (no fabricated data)
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.api.router import router as api_router
import app.models as _models  # noqa: F401  (register all ORM models deterministically)


logger = logging.getLogger("coin87")
# Ensure access logs are emitted by default (institutional audit requirement).
logger.setLevel(logging.INFO)


def create_app() -> FastAPI:
    app = FastAPI(
        title="coin87 Decision Risk API",
        version="1.0.0",
        openapi_url="/openapi.json",
        docs_url=None,
        redoc_url=None,
        description="Institutional decision-risk infrastructure. Read-only. No trade signals.",
    )

    # Allow CORS for Frontend dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.middleware("http")
    async def request_id_and_access_log(request: Request, call_next: Callable):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        start = time.time()
        try:
            response = await call_next(request)
        except OperationalError:
            # Partial DB availability / connection errors: fail safely.
            return JSONResponse(
                status_code=503,
                content={"detail": "Service temporarily unavailable. Data may be stale."},
                headers={"x-request-id": request_id},
            )
        except Exception as e:  # noqa: BLE001
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal error."},
                headers={"x-request-id": request_id},
            )
            logger.exception("Unhandled error", extra={"request_id": request_id})
            return response

        duration_ms = int((time.time() - start) * 1000)
        response.headers["x-request-id"] = request_id

        # Structured access log (no sensitive content).
        logger.info(
            json.dumps(
                {
                    "event": "access",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": getattr(response, "status_code", None),
                    "duration_ms": duration_ms,
                }
            )
        )
        return response

    return app


app = create_app()

