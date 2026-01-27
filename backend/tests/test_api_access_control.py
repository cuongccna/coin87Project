from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.decision_environment_snapshot import DecisionEnvironmentSnapshot, EnvironmentState


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


def test_read_only_can_access_environment(db_session):
    s = DecisionEnvironmentSnapshot(
        snapshot_time=datetime.now(tz=UTC),
        environment_state=EnvironmentState.CLEAN,
        dominant_risks=[],
        risk_density=0,
    )
    db_session.add(s)
    db_session.commit()

    c = TestClient(app)
    r = c.get("/v1/decision/environment", headers=_auth_header("READ_ONLY"))
    assert r.status_code == 200


def test_pm_cannot_access_history(db_session):
    c = TestClient(app)
    r = c.get(
        "/v1/decision/history?start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z",
        headers=_auth_header("PM"),
    )
    assert r.status_code == 403


def test_cio_can_access_history_even_if_empty(db_session):
    c = TestClient(app)
    r = c.get(
        "/v1/decision/history?start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z",
        headers=_auth_header("CIO"),
    )
    assert r.status_code == 200
    assert r.json() == []

