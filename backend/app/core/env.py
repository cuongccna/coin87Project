from __future__ import annotations

import os
from pathlib import Path


def _parse_env_line(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if "=" not in line:
        return None
    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    # Strip optional quotes: KEY="value" or KEY='value'
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    return key, value


def load_env_if_present(*, override: bool = False) -> None:
    """Load .env files into process env if present.

    - Searches repo root `.env` then `backend/.env` (if exist).
    - Does NOT override existing environment variables unless override=True.
    - No external dependency required.
    """

    # backend/app/core/env.py -> backend/app/core -> backend/app -> backend -> repo root
    repo_root = Path(__file__).resolve().parents[3]
    candidates = [
        repo_root / ".env",
        repo_root / "backend" / ".env",
    ]

    for p in candidates:
        if not p.exists() or not p.is_file():
            continue
        try:
            content = p.read_text(encoding="utf-8")
        except OSError:
            continue
        for raw in content.splitlines():
            parsed = _parse_env_line(raw)
            if not parsed:
                continue
            k, v = parsed
            if not override and k in os.environ:
                continue
            os.environ[k] = v

