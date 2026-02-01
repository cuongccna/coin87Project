"""Narrative contamination endpoints (read-only)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import enforce_rate_limit, enforce_read_only_access, get_db_session
from app.repositories.narrative_repo import NarrativeRepository
from app.schemas.narrative import NarrativeDetailResponse, NarrativeResponse, NarrativeRiskResponse
from app.security.auth import require_roles
from app.security.roles import Role


router = APIRouter(
    dependencies=[
        Depends(enforce_read_only_access),
        Depends(require_roles(Role.READ_ONLY, Role.PM, Role.CIO, Role.RISK)),
        Depends(enforce_rate_limit),
    ]
)


@router.get("/narratives", response_model=list[NarrativeResponse])
async def list_narratives(
    min_saturation: int = Query(1, ge=1, le=5),
    active_only: bool = Query(True),
    db: Session = Depends(get_db_session),
) -> list[NarrativeResponse]:
    """List narratives for contamination analysis (no headline browsing)."""
    repo = NarrativeRepository(db)
    if active_only and min_saturation <= 1:
        narratives = await repo.list_active_narratives(limit=200)
    else:
        narratives = await repo.list_narratives_by_saturation(min_saturation, limit=200)
        if active_only:
            narratives = [n for n in narratives if n.status == "ACTIVE"]

    return [
        NarrativeResponse(
            narrative_id=n.id,
            theme=n.theme,
            saturation_level=n.saturation_level,
            status=n.status,  # type: ignore[arg-type]
            first_seen_at=n.first_seen_at,
            last_seen_at=n.last_seen_at,
        )
        for n in narratives
    ]


@router.get("/narratives/{narrative_id}", response_model=NarrativeDetailResponse)
async def get_narrative_detail(
    narrative_id: str,
    db: Session = Depends(get_db_session),
) -> NarrativeDetailResponse:
    """Get a narrative and its currently active linked risks (abstracted)."""
    try:
        nid = uuid.UUID(narrative_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid narrative_id UUID.") from e

    repo = NarrativeRepository(db)
    data = await repo.get_narrative_with_risks(nid)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Narrative not found.")

    # Fetch Audit Trace
    audit_trace_data = await repo.get_audit_trace(nid)

    return NarrativeDetailResponse(
        narrative_id=data.narrative.id,
        theme=data.narrative.theme,
        saturation_level=data.narrative.saturation_level,
        status=data.narrative.status,  # type: ignore[arg-type]
        first_seen_at=data.narrative.first_seen_at,
        last_seen_at=data.narrative.last_seen_at,
        linked_risks=[
            NarrativeRiskResponse(
                risk_type=r.risk_type,
                severity=r.severity,
                recommended_posture=r.recommended_posture,  # type: ignore[arg-type]
                valid_from=r.valid_from,
                valid_to=r.valid_to,
                occurrence_count=r.occurrence_count,
            )
            for r in data.active_risks
        ],
        audit_trace=audit_trace_data,
    )


