from __future__ import annotations

"""Volume sanity check (Job D).

Governance intent:
- Detect sudden drops to zero.
- Detect abnormal spikes.
- Detect narrative cluster explosion.

This check uses a *local baseline* (previous run) stored in audit/state.
No DB writes.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.information_event import InformationEvent
from app.models.decision_risk_event import DecisionRiskEvent
from app.models.decision_environment_snapshot import DecisionEnvironmentSnapshot
from app.models.narrative_cluster import NarrativeCluster


UTC = timezone.utc


def _ratio(now: int, prev: Optional[int]) -> Optional[float]:
    if prev is None or prev <= 0:
        return None
    return float(now) / float(prev)


def run(db: Session, *, now: datetime, baseline: dict[str, Any] | None) -> tuple[str, dict, dict[str, Any]]:
    """Return (status, details, new_baseline)."""
    window_start = now - timedelta(hours=24)

    info_24h = db.execute(
        select(func.count()).select_from(InformationEvent).where(InformationEvent.observed_at >= window_start)
    ).scalar_one()
    risks_24h = db.execute(
        select(func.count()).select_from(DecisionRiskEvent).where(DecisionRiskEvent.detected_at >= window_start)
    ).scalar_one()
    snaps_24h = db.execute(
        select(func.count()).select_from(DecisionEnvironmentSnapshot).where(
            DecisionEnvironmentSnapshot.snapshot_time >= window_start
        )
    ).scalar_one()
    narratives_total = db.execute(select(func.count()).select_from(NarrativeCluster)).scalar_one()

    prev = baseline or {}
    prev_info = prev.get("info_24h")
    prev_risks = prev.get("risks_24h")
    prev_snaps = prev.get("snaps_24h")
    prev_narr = prev.get("narratives_total")

    warnings: list[str] = []
    status = "OK"

    def warn(level: str, msg: str) -> None:
        nonlocal status
        warnings.append(msg)
        if level == "CRITICAL":
            status = "CRITICAL"
        elif level == "DEGRADED" and status != "CRITICAL":
            status = "DEGRADED"

    # Hard sanity
    if info_24h == 0:
        warn("CRITICAL", "24h information_events count is 0 (ingestion likely stalled).")
    if snaps_24h == 0:
        warn("DEGRADED", "24h snapshots count is 0 (snapshot job may be stalled).")

    # Baseline comparisons (conservative, only warn on big deviations)
    for name, cur, prv in [
        ("information_events_24h", info_24h, prev_info),
        ("decision_risk_events_24h", risks_24h, prev_risks),
        ("snapshots_24h", snaps_24h, prev_snaps),
        ("narrative_clusters_total", narratives_total, prev_narr),
    ]:
        r = _ratio(int(cur), int(prv) if isinstance(prv, int) else None)
        if r is None:
            continue
        if r >= 3.0:
            warn("DEGRADED", f"Volume spike detected: {name} ratio={r:.2f} (cur={cur}, prev={prv}).")
        if r <= 0.2:
            warn("DEGRADED", f"Volume drop detected: {name} ratio={r:.2f} (cur={cur}, prev={prv}).")

    details = {
        "window_hours": 24,
        "information_events_24h": int(info_24h),
        "decision_risk_events_24h": int(risks_24h),
        "snapshots_24h": int(snaps_24h),
        "narrative_clusters_total": int(narratives_total),
        "warnings": warnings,
        "baseline_used": bool(baseline),
    }

    new_baseline = {
        "at": now.isoformat(),
        "info_24h": int(info_24h),
        "risks_24h": int(risks_24h),
        "snaps_24h": int(snaps_24h),
        "narratives_total": int(narratives_total),
    }
    return status, details, new_baseline

