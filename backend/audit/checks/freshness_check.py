from __future__ import annotations

"""Data freshness check (Job D).

Governance intent:
- Detect ingestion/derivation/snapshot stalls.
- Warn loudly; never auto-correct.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.information_event import InformationEvent
from app.models.decision_risk_event import DecisionRiskEvent
from app.models.decision_environment_snapshot import DecisionEnvironmentSnapshot


UTC = timezone.utc


@dataclass(frozen=True, slots=True)
class FreshnessResult:
    last_information_event_at: Optional[datetime]
    last_risk_event_at: Optional[datetime]
    last_snapshot_at: Optional[datetime]
    warnings: list[str]


def _age_seconds(now: datetime, ts: Optional[datetime]) -> Optional[int]:
    if ts is None:
        return None
    return max(0, int((now - ts).total_seconds()))


def run(
    db: Session,
    *,
    now: datetime,
    ingest_max_age_minutes: int,
    derive_max_age_minutes: int,
    snapshot_max_age_minutes: int,
) -> tuple[str, dict]:
    """Return (status, details) where status is OK|DEGRADED|CRITICAL."""
    last_info = db.execute(select(func.max(InformationEvent.observed_at))).scalar_one()
    last_risk = db.execute(select(func.max(DecisionRiskEvent.detected_at))).scalar_one()
    last_snap = db.execute(select(func.max(DecisionEnvironmentSnapshot.snapshot_time))).scalar_one()

    warnings: list[str] = []
    status = "OK"

    def warn(level: str, msg: str) -> None:
        nonlocal status
        warnings.append(msg)
        if level == "CRITICAL":
            status = "CRITICAL"
        elif level == "DEGRADED" and status != "CRITICAL":
            status = "DEGRADED"

    if last_info is None:
        warn("CRITICAL", "No information_events present (ingestion appears not running).")
    else:
        age = _age_seconds(now, last_info)
        if age is not None and age > ingest_max_age_minutes * 60:
            warn("DEGRADED", f"Ingestion stalled: last information_event {age}s ago.")

    if last_risk is None:
        warn("DEGRADED", "No decision_risk_events present (derivation may not be running).")
    else:
        age = _age_seconds(now, last_risk)
        if age is not None and age > derive_max_age_minutes * 60:
            warn("DEGRADED", f"Derivation stalled: last decision_risk_event {age}s ago.")

    if last_snap is None:
        warn("DEGRADED", "No decision_environment_snapshots present (snapshot job may not be running).")
    else:
        age = _age_seconds(now, last_snap)
        if age is not None and age > snapshot_max_age_minutes * 60:
            warn("DEGRADED", f"Snapshot lagging: last snapshot {age}s ago.")

    details = {
        "last_information_event_at": last_info.isoformat() if last_info else None,
        "last_risk_event_at": last_risk.isoformat() if last_risk else None,
        "last_snapshot_at": last_snap.isoformat() if last_snap else None,
        "warnings": warnings,
    }
    return status, details

