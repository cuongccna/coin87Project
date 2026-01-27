"""Institutional memory repository (read-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import uuid
from typing import Optional, Sequence

from sqlalchemy import Select, select

from app.models.decision_context import DecisionContext
from app.models.decision_impact_record import DecisionImpactRecord
from app.repositories.base import BaseRepository


@dataclass(frozen=True, slots=True)
class DecisionContextDTO:
    id: str
    context_type: str
    context_time: datetime
    description: Optional[str]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DecisionImpactRecordDTO:
    id: str
    decision_context_id: str
    environment_snapshot_id: Optional[str]
    qualitative_outcome: str
    learning_flags: Optional[list[str]]
    recorded_at: datetime


@dataclass(frozen=True, slots=True)
class DecisionContextWithImpactsDTO:
    context: DecisionContextDTO
    impacts: list[DecisionImpactRecordDTO]


class InstitutionalMemoryRepository(BaseRepository[DecisionContext]):
    """Read-only access for decision contexts and post-decision reflections.

    Institutional use:
    - Post-mortem analysis anchored in formal decision moments.
    - Governance review and learning loops.
    """

    async def list_decision_contexts(
        self, *, start_time: datetime, end_time: datetime, limit: int = 200
    ) -> Sequence[DecisionContextDTO]:
        """List decision contexts in an inclusive time range, newest-first."""
        stmt: Select = (
            select(DecisionContext)
            .where(DecisionContext.context_time >= start_time)
            .where(DecisionContext.context_time <= end_time)
            .order_by(DecisionContext.context_time.desc())
            .limit(limit)
        )
        rows = (await self._execute(stmt)).scalars().all()
        return [_to_context_dto(r) for r in rows]

    async def get_decision_context_with_impacts(
        self, context_id: uuid.UUID
    ) -> Optional[DecisionContextWithImpactsDTO]:
        """Get a decision context and all associated impact records (oldest-first)."""
        stmt_c: Select = select(DecisionContext).where(DecisionContext.id == context_id)
        ctx = (await self._execute(stmt_c)).scalars().first()
        if ctx is None:
            return None

        stmt_i: Select = (
            select(DecisionImpactRecord)
            .where(DecisionImpactRecord.decision_context_id == context_id)
            .order_by(DecisionImpactRecord.recorded_at.asc())
        )
        impacts = (await self._execute(stmt_i)).scalars().all()
        return DecisionContextWithImpactsDTO(
            context=_to_context_dto(ctx),
            impacts=[_to_impact_dto(i) for i in impacts],
        )

    async def list_impact_records_by_flag(
        self, flag: str, *, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None, limit: int = 500
    ) -> Sequence[DecisionImpactRecordDTO]:
        """List impact records where a specific learning flag is present."""
        stmt: Select = select(DecisionImpactRecord).where(
            DecisionImpactRecord.learning_flags.any(flag)
        )
        if start_time is not None:
            stmt = stmt.where(DecisionImpactRecord.recorded_at >= start_time)
        if end_time is not None:
            stmt = stmt.where(DecisionImpactRecord.recorded_at <= end_time)
        stmt = stmt.order_by(DecisionImpactRecord.recorded_at.desc()).limit(limit)
        rows = (await self._execute(stmt)).scalars().all()
        return [_to_impact_dto(r) for r in rows]


def _to_context_dto(m: DecisionContext) -> DecisionContextDTO:
    return DecisionContextDTO(
        id=str(m.id),
        context_type=m.context_type.value,
        context_time=m.context_time,
        description=m.description,
        created_at=m.created_at,
    )


def _to_impact_dto(m: DecisionImpactRecord) -> DecisionImpactRecordDTO:
    return DecisionImpactRecordDTO(
        id=str(m.id),
        decision_context_id=str(m.decision_context_id),
        environment_snapshot_id=str(m.environment_snapshot_id) if m.environment_snapshot_id else None,
        qualitative_outcome=m.qualitative_outcome,
        learning_flags=list(m.learning_flags) if m.learning_flags is not None else None,
        recorded_at=m.recorded_at,
    )

