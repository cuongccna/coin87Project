from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def test_expected_tables_exist(db_session: Session):
    rows = db_session.execute(
        text("select tablename from pg_tables where schemaname='public' order by tablename")
    ).fetchall()
    tables = {r[0] for r in rows}

    expected = {
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
    }
    assert expected.issubset(tables)
    assert "news" not in tables


def test_required_enums_exist(db_session: Session):
    rows = db_session.execute(
        text(
            """
            select t.typname
            from pg_type t
            join pg_namespace n on n.oid = t.typnamespace
            where n.nspname = 'public' and t.typtype = 'e'
            """
        )
    ).fetchall()
    enums = {r[0] for r in rows}

    required = {
        "decision_risk_type_enum",
        "recommended_posture_enum",
        "narrative_status_enum",
        "distortion_type_enum",
        "decision_context_type_enum",
        "environment_state_enum",
    }
    assert required.issubset(enums)


def test_check_constraints_exist(db_session: Session):
    rows = db_session.execute(
        text(
            """
            select conname, conrelid::regclass::text as table_name, pg_get_constraintdef(c.oid) as def
            from pg_constraint c
            where contype = 'c'
            """
        )
    ).fetchall()
    by_table = {}
    for conname, table_name, definition in rows:
        by_table.setdefault(table_name, []).append((conname, definition))

    def has(table: str, needle: str) -> bool:
        return any(needle in d for _, d in by_table.get(table, []))

    assert has("information_events", "octet_length(content_hash_sha256)")
    assert has("decision_risk_events", "severity")
    assert has("decision_risk_events", "valid_to")
    assert has("narrative_clusters", "saturation_level")
    assert has("consensus_pressure_events", "pressure_level")
    assert has("timing_distortion_windows", "window_end")
    assert has("decision_environment_snapshots", "risk_density")

