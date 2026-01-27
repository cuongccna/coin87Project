"""Validate Alembic upgrade + downgrade roundtrip (PostgreSQL).

Usage:
  set DATABASE_URL=postgresql+psycopg://...
  python scripts/validate_migration_roundtrip.py

This script:
- upgrades to head
- verifies expected tables/types exist
- downgrades to base
- verifies tables/types are removed
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[1]

# Make `backend/app` importable as top-level `app` without installing a package.
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.env import load_env_if_present  # noqa: E402


EXPECTED_TABLES = [
    "information_events",
    "decision_risk_events",
    "narrative_clusters",
    "narrative_memberships",
    "consensus_pressure_events",
    "timing_distortion_windows",
    "decision_contexts",
    "decision_environment_snapshots",
    "decision_impact_records",
    "re_evaluation_logs",
]

REQUIRED_ENUMS = [
    "decision_risk_type_enum",
    "recommended_posture_enum",
    "narrative_status_enum",
    "distortion_type_enum",
    "decision_context_type_enum",
    "environment_state_enum",
]


def _alembic_config() -> Config:
    cfg = Config(str(ROOT / "backend" / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "backend" / "alembic"))
    return cfg


def _db_url() -> str:
    load_env_if_present()
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("Missing DATABASE_URL.")
        sys.exit(2)
    return url


def _tables(engine) -> set[str]:
    q = text(
        """
        select tablename
        from pg_tables
        where schemaname = 'public'
        """
    )
    with engine.connect() as c:
        return {r[0] for r in c.execute(q).fetchall()}


def _enums(engine) -> set[str]:
    q = text(
        """
        select t.typname
        from pg_type t
        join pg_namespace n on n.oid = t.typnamespace
        where n.nspname = 'public' and t.typtype = 'e'
        """
    )
    with engine.connect() as c:
        return {r[0] for r in c.execute(q).fetchall()}


def main() -> int:
    url = _db_url()
    cfg = _alembic_config()
    cfg.set_main_option("sqlalchemy.url", url)

    engine = create_engine(url, future=True)

    print("Upgrading to head…")
    command.upgrade(cfg, "head")

    tables = _tables(engine)
    missing_tables = [t for t in EXPECTED_TABLES if t not in tables]
    if missing_tables:
        print("FAIL: missing tables after upgrade:", missing_tables)
        return 1

    enums = _enums(engine)
    missing_enums = [e for e in REQUIRED_ENUMS if e not in enums]
    if missing_enums:
        print("FAIL: missing enums after upgrade:", missing_enums)
        return 1

    print("Downgrading to base…")
    command.downgrade(cfg, "base")

    tables2 = _tables(engine)
    leftover_tables = [t for t in EXPECTED_TABLES if t in tables2]
    if leftover_tables:
        print("FAIL: leftover tables after downgrade:", leftover_tables)
        return 1

    enums2 = _enums(engine)
    leftover_enums = [e for e in REQUIRED_ENUMS if e in enums2]
    if leftover_enums:
        print("FAIL: leftover enums after downgrade:", leftover_enums)
        return 1

    print("PASS: migration roundtrip clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

