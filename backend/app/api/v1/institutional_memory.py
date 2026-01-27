"""Institutional memory endpoints (read-only)."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import enforce_rate_limit, enforce_read_only_access, get_db_session
from app.repositories.decision_environment_repo import DecisionEnvironmentRepository
from app.repositories.institutional_memory_repo import InstitutionalMemoryRepository
from app.schemas.institutional_memory import (
    DecisionContextResponse,
    DecisionHistoryItemResponse,
    DecisionImpactRecordResponse,
)
from app.schemas.decision_environment import DecisionEnvironmentResponse
from app.api.v1.decision_environment import _guidance
from app.security.auth import require_roles
from app.security.roles import Role


router = APIRouter(
    dependencies=[
        Depends(enforce_read_only_access),
        Depends(require_roles(Role.CIO, Role.RISK)),
        Depends(enforce_rate_limit),
    ]
)


@router.get("/history", response_model=list[DecisionHistoryItemResponse])
async def list_decision_history(
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    db: Session = Depends(get_db_session),
) -> list[DecisionHistoryItemResponse]:
    """List decision contexts with associated impact records and environment-at-time."""
    mem_repo = InstitutionalMemoryRepository(db)
    env_repo = DecisionEnvironmentRepository(db)

    contexts = await mem_repo.list_decision_contexts(start_time=start_time, end_time=end_time, limit=200)

    out: list[DecisionHistoryItemResponse] = []
    for ctx in contexts:
        ctx_id = uuid.UUID(ctx.id)
        ctx_with_impacts = await mem_repo.get_decision_context_with_impacts(ctx_id)
        if ctx_with_impacts is None:
            continue

        snap = await env_repo.get_environment_snapshot_at(ctx.context_time)
        env_resp = None
        if snap is not None:
            env_resp = DecisionEnvironmentResponse(
                environment_state=snap.environment_state,  # type: ignore[arg-type]
                dominant_risks=snap.dominant_risks,
                risk_density=snap.risk_density,
                snapshot_time=snap.snapshot_time,
                guidance=_guidance(snap.environment_state, snap.dominant_risks, snap.risk_density),
            )

        out.append(
            DecisionHistoryItemResponse(
                context=DecisionContextResponse(
                    context_id=ctx_with_impacts.context.id,
                    context_type=ctx_with_impacts.context.context_type,
                    context_time=ctx_with_impacts.context.context_time,
                    description=ctx_with_impacts.context.description,
                ),
                decision_environment_at_time=env_resp,
                impacts=[
                    DecisionImpactRecordResponse(
                        recorded_at=i.recorded_at,
                        environment_snapshot_id=i.environment_snapshot_id,
                        qualitative_outcome=i.qualitative_outcome,
                        learning_flags=i.learning_flags or [],
                    )
                    for i in ctx_with_impacts.impacts
                ],
            )
        )

    return out


@router.get("/history/{context_id}", response_model=DecisionHistoryItemResponse)
async def get_decision_history_item(
    context_id: str,
    db: Session = Depends(get_db_session),
) -> DecisionHistoryItemResponse:
    """Get a single decision context with impacts and environment-at-time."""
    try:
        cid = uuid.UUID(context_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid context_id UUID.") from e

    mem_repo = InstitutionalMemoryRepository(db)
    env_repo = DecisionEnvironmentRepository(db)

    ctx = await mem_repo.get_decision_context_with_impacts(cid)
    if ctx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision context not found.")

    snap = await env_repo.get_environment_snapshot_at(ctx.context.context_time)
    env_resp = None
    if snap is not None:
        env_resp = DecisionEnvironmentResponse(
            environment_state=snap.environment_state,  # type: ignore[arg-type]
            dominant_risks=snap.dominant_risks,
            risk_density=snap.risk_density,
            snapshot_time=snap.snapshot_time,
            guidance=_guidance(snap.environment_state, snap.dominant_risks, snap.risk_density),
        )

    return DecisionHistoryItemResponse(
        context=DecisionContextResponse(
            context_id=ctx.context.id,
            context_type=ctx.context.context_type,
            context_time=ctx.context.context_time,
            description=ctx.context.description,
        ),
        decision_environment_at_time=env_resp,
        impacts=[
            DecisionImpactRecordResponse(
                recorded_at=i.recorded_at,
                environment_snapshot_id=i.environment_snapshot_id,
                qualitative_outcome=i.qualitative_outcome,
                learning_flags=i.learning_flags or [],
            )
            for i in ctx.impacts
        ],
    )

