from __future__ import annotations

"""Enum & constraint integrity checks (Job D).

Governance intent:
- Detect unexpected values and obvious integrity violations.
- No repairs; warnings only.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session


def run(db: Session) -> tuple[str, dict]:
    status = "OK"
    warnings: list[str] = []

    def warn(level: str, msg: str) -> None:
        nonlocal status
        warnings.append(msg)
        if level == "CRITICAL":
            status = "CRITICAL"
        elif level == "DEGRADED" and status != "CRITICAL":
            status = "DEGRADED"

    # Orphaned FKs (should be impossible if constraints exist; still check).
    orphan_risks = db.execute(
        text(
            """
            select count(*) from decision_risk_events dre
            left join information_events ie on ie.id = dre.information_event_id
            where ie.id is null
            """
        )
    ).scalar_one()
    if int(orphan_risks) > 0:
        warn("CRITICAL", f"Orphaned decision_risk_events detected: {orphan_risks}.")

    orphan_memberships = db.execute(
        text(
            """
            select count(*) from narrative_memberships nm
            left join narrative_clusters nc on nc.id = nm.narrative_id
            left join decision_risk_events dre on dre.id = nm.decision_risk_event_id
            where nc.id is null or dre.id is null
            """
        )
    ).scalar_one()
    if int(orphan_memberships) > 0:
        warn("CRITICAL", f"Orphaned narrative_memberships detected: {orphan_memberships}.")

    # Non-null checks for key columns (defensive; DB constraints should prevent).
    null_info_source = db.execute(text("select count(*) from information_events where source_ref is null")).scalar_one()
    if int(null_info_source) > 0:
        warn("CRITICAL", f"information_events.source_ref NULL rows: {null_info_source}.")

    # Enum validity checks (should be enforced by Postgres enums; still verify textual values).
    invalid_risk_type = db.execute(
        text(
            """
            select count(*) from decision_risk_events
            where risk_type::text not in ('TIMING_DISTORTION','NARRATIVE_CONTAMINATION','CONSENSUS_TRAP','STRUCTURAL_DECISION_RISK')
            """
        )
    ).scalar_one()
    if int(invalid_risk_type) > 0:
        warn("CRITICAL", f"Invalid decision_risk_events.risk_type values: {invalid_risk_type}.")

    invalid_env_state = db.execute(
        text(
            """
            select count(*) from decision_environment_snapshots
            where environment_state::text not in ('CLEAN','CAUTION','CONTAMINATED')
            """
        )
    ).scalar_one()
    if int(invalid_env_state) > 0:
        warn("CRITICAL", f"Invalid decision_environment_snapshots.environment_state values: {invalid_env_state}.")

    details = {
        "orphaned_decision_risk_events": int(orphan_risks),
        "orphaned_narrative_memberships": int(orphan_memberships),
        "null_information_events_source_ref": int(null_info_source),
        "invalid_decision_risk_type": int(invalid_risk_type),
        "invalid_environment_state": int(invalid_env_state),
        "warnings": warnings,
    }
    return status, details

