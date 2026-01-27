from __future__ import annotations

"""Immutability safety check (Job D).

Governance intent:
- Detect obvious signs of mutation on immutable tables.
- Acknowledge limitations: without DB-level auditing (triggers/WAL/temporal tables),
  it is not possible to *prove* no updates/deletes occurred historically.

This check therefore:
- Verifies immutable tables do not contain an updated_at column (schema-level guard).
- Verifies snapshot times are not in the future.
- Emits warnings if audit coverage is insufficient.
"""

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session


UTC = timezone.utc


def run(db: Session, *, now: datetime) -> tuple[str, dict]:
    status = "OK"
    warnings: list[str] = []

    def warn(level: str, msg: str) -> None:
        nonlocal status
        warnings.append(msg)
        if level == "CRITICAL":
            status = "CRITICAL"
        elif level == "DEGRADED" and status != "CRITICAL":
            status = "DEGRADED"

    # Schema-level: ensure no updated_at columns exist on immutable tables.
    immutable_tables = [
        "information_events",
        "decision_risk_events",
        "decision_environment_snapshots",
        "decision_impact_records",
        "re_evaluation_logs",
        "consensus_pressure_events",
        "timing_distortion_windows",
    ]
    for t in immutable_tables:
        has_updated_at = db.execute(
            text(
                """
                select count(*)
                from information_schema.columns
                where table_schema='public' and table_name=:t and column_name='updated_at'
                """
            ),
            {"t": t},
        ).scalar_one()
        if int(has_updated_at) > 0:
            warn("CRITICAL", f"Immutable table {t} contains updated_at column (unexpected mutability surface).")

    # Temporal sanity: no future snapshots.
    future_snapshots = db.execute(
        text("select count(*) from decision_environment_snapshots where snapshot_time > now() + interval '5 minutes'")
    ).scalar_one()
    if int(future_snapshots) > 0:
        warn("DEGRADED", f"Snapshot time anomalies detected (future snapshots): {future_snapshots}.")

    # Limitation warning (explicit governance transparency).
    warn(
        "DEGRADED",
        "Immutability cannot be cryptographically proven without DB-level audit triggers/WAL retention; "
        "this check is schema+sanity only.",
    )

    details = {
        "checked_tables": immutable_tables,
        "future_snapshots": int(future_snapshots),
        "warnings": warnings,
    }
    return status, details

