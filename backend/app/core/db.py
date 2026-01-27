"""Database configuration (PostgreSQL only).

Phase 1 scope:
- Provide a deterministic SQLAlchemy 2.0 engine and session factory used by
  Alembic migrations and future application layers.

Constraints:
- Configuration is via environment variables only (.env loaded by process runner).
"""

from __future__ import annotations

import os
from typing import Final

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.env import load_env_if_present


DATABASE_URL_ENV: Final[str] = "DATABASE_URL"


def get_database_url() -> str:
    load_env_if_present()
    url = os.environ.get(DATABASE_URL_ENV)
    if not url:
        raise RuntimeError(
            f"Missing required env var {DATABASE_URL_ENV}. "
            "Example: postgresql+psycopg://user:pass@host:5432/coin87"
        )
    return url


def create_db_engine() -> Engine:
    return create_engine(
        get_database_url(),
        pool_pre_ping=True,
        future=True,
    )


ENGINE: Engine = create_db_engine()

SessionLocal = sessionmaker(bind=ENGINE, class_=Session, autoflush=False, autocommit=False)

