from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app


UTC = timezone.utc


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("C87_JWT_SECRET", "test-secret")


def _auth_header(role: str) -> dict[str, str]:
    from conftest import make_jwt

    token = make_jwt(
        sub="test",
        role=role,
        secret=os.environ["C87_JWT_SECRET"],
        exp=int((datetime.now(tz=UTC) + timedelta(hours=1)).timestamp()),
    )
    return {"Authorization": f"Bearer {token}"}


def test_db_operational_error_returns_503(monkeypatch: pytest.MonkeyPatch):
    from app.api.v1 import decision_environment as mod

    async def boom(*args, **kwargs):
        raise OperationalError("select 1", {}, Exception("down"))

    monkeypatch.setattr(mod.DecisionEnvironmentRepository, "get_latest_environment_snapshot", boom)

    c = TestClient(app)
    r = c.get("/v1/decision/environment", headers=_auth_header("READ_ONLY"))
    assert r.status_code == 503
    assert "stale" in r.json()["detail"].lower()

