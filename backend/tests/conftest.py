from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Generator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


ROOT = Path(__file__).resolve().parents[2]

# Ensure `backend/app` is importable as top-level `app` for tests.
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.env import load_env_if_present  # noqa: E402


def _db_url() -> str | None:
    load_env_if_present()
    return os.environ.get("DATABASE_URL")


def _alembic_config(db_url: str) -> Config:
    cfg = Config(str(ROOT / "backend" / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "backend" / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


@pytest.fixture(scope="session")
def engine() -> Engine:
    url = _db_url()
    if not url:
        pytest.skip("DATABASE_URL not set; skipping DB integration tests.")
    return create_engine(url, future=True)


@pytest.fixture(scope="session", autouse=True)
def migrate_db(engine: Engine) -> Generator[None, None, None]:
    """Ensure schema is upgraded to head for the test session."""
    url = _db_url()
    assert url is not None
    cfg = _alembic_config(url)
    command.upgrade(cfg, "head")
    yield


@pytest.fixture()
def db_session(engine: Engine) -> Generator[Session, None, None]:
    """DB session per test with rollback."""
    SessionLocal = sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False)
    session = SessionLocal()
    trans = session.begin()
    try:
        yield session
    finally:
        if trans.is_active:
            trans.rollback()
        session.close()


def make_jwt(sub: str, role: str, secret: str, *, exp: int | None = None) -> str:
    """HS256 JWT generator for API tests (no external dependency)."""
    import base64, hashlib, hmac, json, time  # noqa: E401

    def b64url(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": sub, "role": role}
    if exp is not None:
        payload["exp"] = exp

    header_b64 = b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{b64url(sig)}"

