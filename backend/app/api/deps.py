"""API dependencies (read-only).

Institutional rationale:
- Centralize access control and read-only enforcement.
- Prevent accidental writes from request paths.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any, Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.security.auth import Principal, get_current_principal
from app.security.rate_limit import LIMITER


def get_db_session() -> Generator[Session, None, None]:
    """Provide a database session for request scope (read-only discipline)."""
    session: Session = SessionLocal()
    try:
        # Hard disable autoflush to reduce accidental writes on relationship access.
        session.autoflush = False
        yield session
    finally:
        session.close()


def get_current_user() -> Optional[dict[str, Any]]:
    """Auth stub (no auth logic in this phase)."""
    return None


def enforce_read_only_access(request: Request, db: Session = Depends(get_db_session)) -> None:
    """Reject non-read methods and any session state that indicates writes."""
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail="Read-only API.")
    if db.new or db.dirty or db.deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Read-only invariant violated: pending DB changes detected.",
        )


def enforce_rate_limit(principal: Principal = Depends(get_current_principal)) -> None:
    """Enforce conservative per-token hourly request budget."""
    LIMITER.check(principal.token_fingerprint)

