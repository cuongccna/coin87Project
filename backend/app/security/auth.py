"""Authentication & authorization (institutional, token-based).

Design:
- Bearer JWT tokens (HS256) provisioned manually out-of-band.
- Role is embedded in token claims.
- Default deny. Endpoints must explicitly allow roles.
"""

from __future__ import annotations

import base64
import hmac
import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from fastapi import Depends, HTTPException, Request, status

from app.security.roles import Role, is_role_allowed


class AuthError(HTTPException):
    pass


@dataclass(frozen=True, slots=True)
class Principal:
    """Authenticated principal extracted from token claims."""

    sub: str
    role: Role
    token_fingerprint: str  # stable, non-sensitive identifier for rate limiting/audit logs


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _get_jwt_secret() -> bytes:
    secret = os.environ.get("C87_JWT_SECRET")
    if not secret:
        raise RuntimeError("Missing required env var C87_JWT_SECRET.")
    return secret.encode("utf-8")


def _hmac_sha256(key: bytes, msg: bytes) -> bytes:
    return hmac.new(key, msg, hashlib.sha256).digest()


def decode_and_verify_jwt(token: str) -> dict[str, Any]:
    """Verify HS256 JWT signature and minimal standard claims.

    Required claims:
    - sub: subject identifier
    - role: one of Role
    Optional:
    - exp: unix epoch seconds
    """
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError as e:
        raise AuthError(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format.") from e

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = _b64url_encode(_hmac_sha256(_get_jwt_secret(), signing_input))
    if not hmac.compare_digest(expected_sig, sig_b64):
        raise AuthError(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature.")

    try:
        header = json.loads(_b64url_decode(header_b64))
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception as e:  # noqa: BLE001
        raise AuthError(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token encoding.") from e

    if header.get("alg") != "HS256" or header.get("typ") != "JWT":
        raise AuthError(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unsupported token header.")

    exp = payload.get("exp")
    if exp is not None:
        try:
            exp_i = int(exp)
        except (TypeError, ValueError) as e:
            raise AuthError(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid exp claim.") from e
        if int(time.time()) >= exp_i:
            raise AuthError(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired.")

    if "sub" not in payload or "role" not in payload:
        raise AuthError(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing required claims.")

    return payload


def token_fingerprint(token: str) -> str:
    """Non-reversible token fingerprint for rate limiting and audit logs."""
    raw = hashlib.sha256(token.encode("utf-8")).digest()
    return _b64url_encode(raw[:18])  # short, stable


def get_current_principal(request: Request) -> Principal:
    """Extract and validate bearer token, returning Principal."""
    auth = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise AuthError(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")
    token = auth.split(" ", 1)[1].strip()
    if not token:
        raise AuthError(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")

    claims = decode_and_verify_jwt(token)
    try:
        role = Role(str(claims["role"]))
    except Exception as e:  # noqa: BLE001
        raise AuthError(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid role claim.") from e

    sub = str(claims["sub"])
    if not sub:
        raise AuthError(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid sub claim.")

    return Principal(sub=sub, role=role, token_fingerprint=token_fingerprint(token))


def require_roles(*allowed_roles: Role) -> Callable[[Principal], Principal]:
    """FastAPI dependency factory enforcing explicit allow-list."""

    allowed = set(allowed_roles)

    def _dep(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not is_role_allowed(principal.role, allowed):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        return principal

    return _dep


def maybe_get_principal(request: Request) -> Optional[Principal]:
    """Optional principal for endpoints that allow anonymous access in future.

    Not used in current institutional mode (default deny elsewhere).
    """
    auth = request.headers.get("authorization")
    if not auth:
        return None
    try:
        return get_current_principal(request)
    except HTTPException:
        return None

