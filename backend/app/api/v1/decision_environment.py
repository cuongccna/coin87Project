"""Decision environment endpoints (read-only).

Institutional use:
These endpoints provide a low-noise snapshot suitable for IC pre-checks and
dashboard embedding. They do not expose raw inputs.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import enforce_rate_limit, enforce_read_only_access, get_db_session
from app.repositories.decision_environment_repo import DecisionEnvironmentRepository
from app.schemas.decision_environment import DecisionEnvironmentResponse
from app.security.auth import require_roles
from app.security.roles import Role


UTC = timezone.utc

router = APIRouter(
    dependencies=[
        Depends(enforce_read_only_access),
        Depends(require_roles(Role.READ_ONLY, Role.PM, Role.CIO, Role.RISK)),
        Depends(enforce_rate_limit),
    ]
)


def _guidance(environment_state: str, dominant_risks: list[str], risk_density: int) -> str:
    if environment_state == "CLEAN":
        return "No action recommended. Continue normal diligence cadence."
    if environment_state == "CAUTION":
        if dominant_risks:
            return "Review with caution. Consider delaying decisions sensitive to: " + ", ".join(dominant_risks) + "."
        return "Review with caution. Information environment is uncertain."
    # CONTAMINATED
    if dominant_risks:
        return "Delay discretionary decisions. Dominant decision risk(s): " + ", ".join(dominant_risks) + "."
    return "Delay discretionary decisions. Information environment is contaminated."


def _staleness(snapshot_time: datetime) -> tuple[bool, int]:
    now = datetime.now(tz=UTC)
    delta = now - snapshot_time
    seconds = max(0, int(delta.total_seconds()))
    # Conservative default: treat > 2 hours as stale unless operators tighten via policy.
    return seconds > 2 * 3600, seconds


@router.get("/environment", response_model=DecisionEnvironmentResponse)
async def get_environment(db: Session = Depends(get_db_session)) -> DecisionEnvironmentResponse:
    repo = DecisionEnvironmentRepository(db)
    snap = await repo.get_latest_environment_snapshot()
    if snap is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No environment snapshot available.")
    stale, staleness_seconds = _staleness(snap.snapshot_time)
    return DecisionEnvironmentResponse(
        environment_state=snap.environment_state,  # type: ignore[arg-type]
        dominant_risks=snap.dominant_risks,
        risk_density=snap.risk_density,
        snapshot_time=snap.snapshot_time,
        guidance=_guidance(snap.environment_state, snap.dominant_risks, snap.risk_density),
        data_stale=stale,
        staleness_seconds=staleness_seconds,
    )


@router.get("/environment/{timestamp}", response_model=DecisionEnvironmentResponse)
async def get_environment_at(
    timestamp: datetime, db: Session = Depends(get_db_session)
) -> DecisionEnvironmentResponse:
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="timestamp must be timezone-aware UTC.")
    if timestamp.utcoffset() != UTC.utcoffset(timestamp):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="timestamp must be UTC.")

    repo = DecisionEnvironmentRepository(db)
    snap = await repo.get_environment_snapshot_at(timestamp.astimezone(UTC))
    if snap is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No environment snapshot available at that time.")
    stale, staleness_seconds = _staleness(snap.snapshot_time)
    return DecisionEnvironmentResponse(
        environment_state=snap.environment_state,  # type: ignore[arg-type]
        dominant_risks=snap.dominant_risks,
        risk_density=snap.risk_density,
        snapshot_time=snap.snapshot_time,
        guidance=_guidance(snap.environment_state, snap.dominant_risks, snap.risk_density),
        data_stale=stale,
        staleness_seconds=staleness_seconds,
    )

