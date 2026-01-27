from __future__ import annotations

"""Snapshot consistency check (Job D).

Checks:
- Snapshot ordering monotonic by snapshot_time.
- No duplicate identical snapshots (adjacent duplicates).
- Snapshot frequency within bounds (24h window count).
"""

from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.decision_environment_snapshot import DecisionEnvironmentSnapshot


def run(db: Session, *, now: datetime, min_snapshots_24h: int = 1, max_snapshots_24h: int = 500) -> tuple[str, dict]:
    status = "OK"
    warnings: list[str] = []

    def warn(level: str, msg: str) -> None:
        nonlocal status
        warnings.append(msg)
        if level == "CRITICAL":
            status = "CRITICAL"
        elif level == "DEGRADED" and status != "CRITICAL":
            status = "DEGRADED"

    # Monotonic ordering check (pull recent N).
    recent = list(
        db.execute(
            select(
                DecisionEnvironmentSnapshot.snapshot_time,
                DecisionEnvironmentSnapshot.environment_state,
                DecisionEnvironmentSnapshot.dominant_risks,
                DecisionEnvironmentSnapshot.risk_density,
            )
            .order_by(DecisionEnvironmentSnapshot.snapshot_time.desc())
            .limit(200)
        ).all()
    )

    # Reverse to chronological.
    recent_chrono = list(reversed(recent))
    last_t = None
    duplicates = 0
    prev_sig = None
    for t, state, dom, dens in recent_chrono:
        if last_t is not None and t < last_t:
            warn("CRITICAL", "Snapshot times are not monotonic (ordering anomaly).")
            break
        last_t = t
        sig = (str(state), list(dom or []), int(dens))
        if prev_sig is not None and sig == prev_sig:
            duplicates += 1
        prev_sig = sig

    if duplicates > 0:
        warn("DEGRADED", f"Adjacent duplicate snapshots detected (count={duplicates}).")

    # Frequency bounds (24h)
    window_start = now - timedelta(hours=24)
    snaps_24h = db.execute(
        select(func.count()).select_from(DecisionEnvironmentSnapshot).where(
            DecisionEnvironmentSnapshot.snapshot_time >= window_start
        )
    ).scalar_one()
    if int(snaps_24h) < int(min_snapshots_24h):
        warn("DEGRADED", f"Snapshots in last 24h below expected: {snaps_24h}.")
    if int(snaps_24h) > int(max_snapshots_24h):
        warn("DEGRADED", f"Snapshots in last 24h above expected: {snaps_24h}.")

    details = {
        "recent_checked": len(recent),
        "adjacent_duplicate_count": int(duplicates),
        "snapshots_24h": int(snaps_24h),
        "warnings": warnings,
    }
    return status, details

