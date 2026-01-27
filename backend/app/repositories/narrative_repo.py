"""Narrative repository (read-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid
from typing import Optional, Sequence

from sqlalchemy import Select, select

from app.models.narrative_cluster import NarrativeCluster, NarrativeStatus, narrative_memberships
from app.models.decision_risk_event import DecisionRiskEvent
from app.repositories.base import BaseRepository


UTC = timezone.utc


@dataclass(frozen=True, slots=True)
class NarrativeDTO:
    id: str
    theme: str
    first_seen_at: datetime
    last_seen_at: datetime
    saturation_level: int
    status: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class NarrativeWithRisksDTO:
    narrative: NarrativeDTO
    active_risks: list["NarrativeRiskDTO"]


@dataclass(frozen=True, slots=True)
class NarrativeRiskDTO:
    id: str
    risk_type: str
    severity: int
    affected_decisions: list[str]
    recommended_posture: str
    detected_at: datetime
    valid_from: datetime
    valid_to: Optional[datetime]


class NarrativeRepository(BaseRepository[NarrativeCluster]):
    """Read-only access for narratives and their linked risks."""

    async def list_active_narratives(self, *, limit: int = 200) -> Sequence[NarrativeDTO]:
        """List ACTIVE narratives ordered by saturation and recency."""
        stmt: Select = (
            select(NarrativeCluster)
            .where(NarrativeCluster.status == NarrativeStatus.ACTIVE)
            .order_by(NarrativeCluster.saturation_level.desc(), NarrativeCluster.last_seen_at.desc())
            .limit(limit)
        )
        rows = (await self._execute(stmt)).scalars().all()
        return [_to_narrative_dto(r) for r in rows]

    async def list_narratives_by_saturation(
        self, min_level: int, *, limit: int = 200
    ) -> Sequence[NarrativeDTO]:
        """List narratives with saturation at or above a threshold."""
        stmt: Select = (
            select(NarrativeCluster)
            .where(NarrativeCluster.saturation_level >= min_level)
            .order_by(NarrativeCluster.saturation_level.desc(), NarrativeCluster.last_seen_at.desc())
            .limit(limit)
        )
        rows = (await self._execute(stmt)).scalars().all()
        return [_to_narrative_dto(r) for r in rows]

    async def get_narrative_with_risks(self, narrative_id: uuid.UUID) -> Optional[NarrativeWithRisksDTO]:
        """Fetch a narrative with active linked DecisionRiskEvents (as of now).

        By default, expired risks are excluded to keep outputs time-relevant for IC usage.
        """
        now = datetime.now(tz=UTC)

        stmt_n: Select = select(NarrativeCluster).where(NarrativeCluster.id == narrative_id)
        narrative = (await self._execute(stmt_n)).scalars().first()
        if narrative is None:
            return None

        stmt_r: Select = (
            select(DecisionRiskEvent)
            .join(
                narrative_memberships,
                DecisionRiskEvent.id == narrative_memberships.c.decision_risk_event_id,
            )
            .where(narrative_memberships.c.narrative_id == narrative_id)
            .where(DecisionRiskEvent.valid_from <= now)
            .where((DecisionRiskEvent.valid_to.is_(None)) | (DecisionRiskEvent.valid_to > now))
            .order_by(DecisionRiskEvent.severity.desc(), DecisionRiskEvent.detected_at.desc())
        )
        risks = (await self._execute(stmt_r)).scalars().all()
        return NarrativeWithRisksDTO(
            narrative=_to_narrative_dto(narrative),
            active_risks=[_to_narrative_risk_dto(r) for r in risks],
        )


def _to_narrative_dto(m: NarrativeCluster) -> NarrativeDTO:
    return NarrativeDTO(
        id=str(m.id),
        theme=m.theme,
        first_seen_at=m.first_seen_at,
        last_seen_at=m.last_seen_at,
        saturation_level=int(m.saturation_level),
        status=m.status.value,
        created_at=m.created_at,
    )


def _to_narrative_risk_dto(m: DecisionRiskEvent) -> NarrativeRiskDTO:
    return NarrativeRiskDTO(
        id=str(m.id),
        risk_type=m.risk_type.value,
        severity=int(m.severity),
        affected_decisions=list(m.affected_decisions),
        recommended_posture=m.recommended_posture.value,
        detected_at=m.detected_at,
        valid_from=m.valid_from,
        valid_to=m.valid_to,
    )

