from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
import app.main as main_mod
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


def test_request_id_propagates_and_logs_are_sanitized(db_session, caplog):
    s = DecisionEnvironmentSnapshot(
        snapshot_time=datetime.now(tz=UTC),
        environment_state=EnvironmentState.CLEAN,
        dominant_risks=[],
        risk_density=0,
    )
    db_session.add(s)
    db_session.commit()

    captured: list[str] = []
    orig_info = main_mod.logger.info

    def _capture_info(msg, *args, **kwargs):
        captured.append(str(msg))
        return orig_info(msg, *args, **kwargs)

    # Capture access log emission regardless of handler wiring.
    main_mod.logger.setLevel(__import__("logging").INFO)
    main_mod.logger.info = _capture_info  # type: ignore[method-assign]

    c = TestClient(app)
    r = c.get("/v1/decision/environment", headers=_auth_header("READ_ONLY"))
    assert r.status_code == 200
    assert "x-request-id" in r.headers
    main_mod.logger.info = orig_info  # type: ignore[method-assign]

    # Find JSON access log line.
    access_lines = [m for m in captured if '"event": "access"' in m]
    assert access_lines, "No access logs captured."

    payload = json.loads(access_lines[-1])
    assert payload["event"] == "access"
    assert payload["path"] == "/v1/decision/environment"
    assert "authorization" not in access_lines[-1].lower()

