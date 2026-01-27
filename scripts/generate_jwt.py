"""Generate HS256 JWT compatible with coin87 backend (no external deps).

Usage (PowerShell):
  $env:C87_JWT_SECRET="your-secret"
  python scripts/generate_jwt.py --role READ_ONLY --sub ui

Then put output token into frontend/.env.local as C87_UI_BEARER_TOKEN.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import time


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def make_jwt(*, sub: str, role: str, secret: str, exp_seconds: int) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": sub, "role": role, "exp": int(time.time()) + exp_seconds}

    header_b64 = b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{b64url(sig)}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sub", required=True)
    ap.add_argument("--role", required=True, choices=["READ_ONLY", "PM", "CIO", "RISK"])
    ap.add_argument("--exp-seconds", type=int, default=60 * 60 * 12)  # 12h
    args = ap.parse_args()

    secret = os.environ.get("C87_JWT_SECRET")
    if not secret:
        raise SystemExit("Missing C87_JWT_SECRET in environment.")

    token = make_jwt(sub=args.sub, role=args.role, secret=secret, exp_seconds=args.exp_seconds)
    print(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

