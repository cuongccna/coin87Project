"""Minimal API smoke to validate access logging and auth."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.env import load_env_if_present  # noqa: E402
from app.main import app  # noqa: E402


def make_jwt(sub: str, role: str, secret: str, *, exp: int | None = None) -> str:
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


class ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def main() -> int:
    load_env_if_present()
    os.environ.setdefault("C87_JWT_SECRET", "test-secret")

    logger = logging.getLogger("coin87")
    logger.setLevel(logging.INFO)
    h = ListHandler()
    h_stream = logging.StreamHandler()
    h_stream.setLevel(logging.INFO)
    h_stream.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(h)
    logger.addHandler(h_stream)

    token = make_jwt(sub="smoke", role="READ_ONLY", secret=os.environ["C87_JWT_SECRET"], exp=int(time.time()) + 3600)
    c = TestClient(app, raise_server_exceptions=True)
    try:
        r = c.get("/v1/decision/environment", headers={"Authorization": f"Bearer {token}"})
        print("status:", r.status_code)
        print("x-request-id:", r.headers.get("x-request-id"))
        print("body:", r.text[:300])
    except Exception as ex:  # noqa: BLE001
        print("EXCEPTION:", type(ex).__name__, str(ex))

    logger.removeHandler(h)
    logger.removeHandler(h_stream)
    print("coin87 logs:", h.messages[-3:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

