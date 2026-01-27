from __future__ import annotations

"""Risk aggregation for Job C.

STRICT:
- READ-only from decision_risk_events and narrative_clusters.
- No external calls.
- Deterministic, conservative output.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.decision_risk_event import DecisionRiskEvent, RiskType
from app.models.narrative_cluster import NarrativeCluster, NarrativeStatus


@dataclass(frozen=True, slots=True)
class AggregatedSignals:
    active_risk_count: int
    active_risk_types: list[str]              # RiskType values as strings
    dominant_risk_categories: list[str]       # max 3
    any_high_severity: bool
    medium_category_count: int
    timing_distortion_present: bool
    narrative_active_high_saturation: bool
    narrative_active_elevated: bool


def _severity_band(sev: int) -> str:
    if sev >= 4:
        return "high"
    if sev == 3:
        return "medium"
    return "low"


def fetch_active_risks(db: Session, *, snapshot_time: datetime) -> list[DecisionRiskEvent]:
    """Active risk window: valid_from <= t and (valid_to is null or valid_to > t)."""
    stmt = select(DecisionRiskEvent).where(
        and_(
            DecisionRiskEvent.valid_from <= snapshot_time,
            or_(DecisionRiskEvent.valid_to.is_(None), DecisionRiskEvent.valid_to > snapshot_time),
        )
    )
    return list(db.execute(stmt).scalars().all())


def aggregate(db: Session, *, snapshot_time: datetime) -> AggregatedSignals:
    risks = fetch_active_risks(db, snapshot_time=snapshot_time)
    active_risk_count = len(risks)

    # Category counts (presence only; no hype weighting).
    by_type: dict[str, int] = {}
    any_high = False
    medium_types: set[str] = set()
    timing_present = False

    for r in risks:
        k = str(r.risk_type)
        by_type[k] = by_type.get(k, 0) + 1
        band = _severity_band(int(r.severity))
        if band == "high":
            any_high = True
        if band == "medium":
            medium_types.add(k)
        if r.risk_type == RiskType.TIMING_DISTORTION:
            timing_present = True

    dominant = [k for k, _ in sorted(by_type.items(), key=lambda kv: (-kv[1], kv[0]))][:3]

    # Narrative influence is indirect (context only).
    nar_stmt = select(NarrativeCluster.status, NarrativeCluster.saturation_level).where(
        NarrativeCluster.status.in_([NarrativeStatus.ACTIVE])
    )
    nar_rows = db.execute(nar_stmt).all()
    elevated = any(int(sat) >= 3 for _, sat in nar_rows)
    high_sat = any(int(sat) >= 4 for _, sat in nar_rows)

    return AggregatedSignals(
        active_risk_count=active_risk_count,
        active_risk_types=sorted(by_type.keys()),
        dominant_risk_categories=dominant,
        any_high_severity=any_high,
        medium_category_count=len(medium_types),
        timing_distortion_present=timing_present,
        narrative_active_high_saturation=high_sat,
        narrative_active_elevated=elevated,
    )

