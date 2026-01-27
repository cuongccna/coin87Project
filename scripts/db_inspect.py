"""Inspect coin87 database objects (debug helper)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.env import load_env_if_present  # noqa: E402


def main() -> int:
    load_env_if_present()
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("Missing DATABASE_URL.")
        return 2

    engine = create_engine(url, future=True, pool_pre_ping=True)
    with engine.connect() as c:
        public_tables = [
            r[0]
            for r in c.execute(
                text("select tablename from pg_tables where schemaname='public' order by tablename")
            ).fetchall()
        ]
        print("public tables:", public_tables)

        coin87_tables = c.execute(
            text(
                """
                select table_schema, table_name
                from information_schema.tables
                where table_type = 'BASE TABLE'
                  and table_name in (
                    'information_events',
                    'decision_risk_events',
                    'narrative_clusters',
                    'narrative_memberships',
                    'consensus_pressure_events',
                    'timing_distortion_windows',
                    'decision_contexts',
                    'decision_environment_snapshots',
                    'decision_impact_records',
                    're_evaluation_logs',
                    'alembic_version'
                  )
                order by table_schema, table_name
                """
            )
        ).fetchall()
        print("coin87 tables (any schema):", coin87_tables)

        enums_any = c.execute(
            text(
                "select n.nspname, t.typname from pg_type t join pg_namespace n on n.oid=t.typnamespace "
                "where t.typtype='e' order by n.nspname, t.typname"
            )
        ).fetchall()
        print("enum types (all schemas):", enums_any)

        try:
            vers = c.execute(text("select version_num from alembic_version")).fetchall()
            print("alembic_version:", vers)
        except Exception as ex:  # noqa: BLE001
            print("alembic_version: (missing or unreadable)", type(ex).__name__, str(ex))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

