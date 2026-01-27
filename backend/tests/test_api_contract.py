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

    token = make_jwt(sub="test", role=role, secret=os.environ["C87_JWT_SECRET"], exp=int((datetime.now(tz=UTC) + timedelta(hours=1)).timestamp()))
    return {"Authorization": f"Bearer {token}"}


def test_openapi_has_no_non_get_operations():
    c = TestClient(app)
    spec = c.get("/openapi.json").json()

    assert "paths" in spec
    for path, methods in spec["paths"].items():
        if not path.startswith("/v1/decision"):
            continue
        for m in methods.keys():
            assert m.lower() in {"get"}, f"Non-GET method found in OpenAPI: {path} {m}"


def test_environment_response_shape(db_session):
    # Seed one snapshot so /environment returns 200.
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
    body = r.json()

    # No internal DB fields.
    assert "id" not in body
    assert "created_at" not in body

    # Required fields.
    assert set(body.keys()) >= {
        "environment_state",
        "dominant_risks",
        "risk_density",
        "snapshot_time",
        "guidance",
    }

