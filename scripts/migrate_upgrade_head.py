"""Upgrade Alembic to head (safe migrate; no downgrade).

Usage:
  python scripts/migrate_upgrade_head.py

Reads DATABASE_URL from:
- existing environment
- or `.env` (repo root) / `backend/.env` via app.core.env.load_env_if_present()
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.env import load_env_if_present  # noqa: E402


def main() -> int:
    load_env_if_present()
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("Missing DATABASE_URL (set env var or create .env).")
        return 2

    cfg = Config(str(ROOT / "backend" / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "backend" / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)

    print("Upgrading Alembic to head…")
    command.upgrade(cfg, "head")
    print("PASS: upgraded to head.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

