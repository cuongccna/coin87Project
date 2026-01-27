"""Decision risk repository (read-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import Select, and_, or_, select

from app.models.decision_risk_event import DecisionRiskEvent
from app.repositories.base import BaseRepository


UTC = timezone.utc


@dataclass(frozen=True, slots=True)
class DecisionRiskDTO:
    id: str
    risk_type: str
    severity: int
    affected_decisions: list[str]
    recommended_posture: str
    detected_at: datetime
    valid_from: datetime
    valid_to: Optional[datetime]
    created_at: datetime


class DecisionRiskRepository(BaseRepository[DecisionRiskEvent]):
    """Read-only access for decision risk events.

    Institutional use:
    - Surface risks that contaminate discretionary decision-making.
    - Never expose raw InformationEvents via repository returns.
    """

    async def list_active_risks(self, at_time: Optional[datetime] = None, *, limit: int = 500) -> Sequence[DecisionRiskDTO]:
        """List active risks at a point in time (defaults to now)."""
        t = at_time or datetime.now(tz=UTC)
        stmt: Select = (
            select(DecisionRiskEvent)
            .where(_active_at(DecisionRiskEvent, t))
            .order_by(DecisionRiskEvent.severity.desc(), DecisionRiskEvent.detected_at.desc())
            .limit(limit)
        )
        rows = (await self._execute(stmt)).scalars().all()
        return [_to_risk_dto(r) for r in rows]

    async def list_risks_by_decision_type(
        self, decision_type: str, at_time: Optional[datetime] = None, *, limit: int = 500
    ) -> Sequence[DecisionRiskDTO]:
        """List active risks relevant to a specific decision type (e.g., 'allocation')."""
        t = at_time or datetime.now(tz=UTC)
        stmt: Select = (
            select(DecisionRiskEvent)
            .where(_active_at(DecisionRiskEvent, t))
            .where(DecisionRiskEvent.affected_decisions.any(decision_type))
            .order_by(DecisionRiskEvent.severity.desc(), DecisionRiskEvent.detected_at.desc())
            .limit(limit)
        )
        rows = (await self._execute(stmt)).scalars().all()
        return [_to_risk_dto(r) for r in rows]

    async def list_risks_by_severity(
        self, min_severity: int, at_time: Optional[datetime] = None, *, limit: int = 500
    ) -> Sequence[DecisionRiskDTO]:
        """List active risks at or above a severity threshold."""
        t = at_time or datetime.now(tz=UTC)
        stmt: Select = (
            select(DecisionRiskEvent)
            .where(_active_at(DecisionRiskEvent, t))
            .where(DecisionRiskEvent.severity >= min_severity)
            .order_by(DecisionRiskEvent.severity.desc(), DecisionRiskEvent.detected_at.desc())
            .limit(limit)
        )
        rows = (await self._execute(stmt)).scalars().all()
        return [_to_risk_dto(r) for r in rows]


def _active_at(model: type[DecisionRiskEvent], t: datetime):
    return and_(
        model.valid_from <= t,
        or_(model.valid_to.is_(None), model.valid_to > t),
    )


def _to_risk_dto(m: DecisionRiskEvent) -> DecisionRiskDTO:
    return DecisionRiskDTO(
        id=str(m.id),
        risk_type=m.risk_type.value,
        severity=int(m.severity),
        affected_decisions=list(m.affected_decisions),
        recommended_posture=m.recommended_posture.value,
        detected_at=m.detected_at,
        valid_from=m.valid_from,
        valid_to=m.valid_to,
        created_at=m.created_at,
    )

