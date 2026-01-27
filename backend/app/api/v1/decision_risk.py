"""Decision risk endpoints (read-only)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import enforce_rate_limit, enforce_read_only_access, get_db_session
from app.repositories.decision_risk_repo import DecisionRiskRepository
from app.schemas.decision_risk import DecisionRiskEventResponse, TimeRelevance
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


@router.get("/risk-events", response_model=list[DecisionRiskEventResponse])
async def list_risk_events(
    min_severity: int = Query(3, ge=1, le=5),
    decision_type: Optional[str] = Query(None, min_length=1, max_length=64),
    at_time: Optional[datetime] = None,
    db: Session = Depends(get_db_session),
) -> list[DecisionRiskEventResponse]:
    """List active decision risks with conservative defaults."""
    if at_time is not None:
        if at_time.tzinfo is None or at_time.utcoffset() is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="at_time must be timezone-aware UTC.",
            )
        if at_time.utcoffset() != UTC.utcoffset(at_time):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="at_time must be UTC.",
            )
        t = at_time.astimezone(UTC)
    else:
        t = None

    repo = DecisionRiskRepository(db)

    if decision_type is not None:
        risks = await repo.list_risks_by_decision_type(decision_type, t, limit=500)
        risks = [r for r in risks if r.severity >= min_severity]
    else:
        risks = await repo.list_risks_by_severity(min_severity, t, limit=500)

    return [
        DecisionRiskEventResponse(
            risk_type=r.risk_type,
            severity=r.severity,
            affected_decisions=r.affected_decisions,
            recommended_posture=r.recommended_posture,  # type: ignore[arg-type]
            detected_at=r.detected_at,
            time_relevance=TimeRelevance(valid_from=r.valid_from, valid_to=r.valid_to),
        )
        for r in risks
    ]

