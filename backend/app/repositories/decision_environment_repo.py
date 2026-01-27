"""Decision environment repository (read-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import Select, select

from app.models.decision_environment_snapshot import DecisionEnvironmentSnapshot
from app.repositories.base import BaseRepository


@dataclass(frozen=True, slots=True)
class EnvironmentSnapshotDTO:
    id: str
    snapshot_time: datetime
    environment_state: str
    dominant_risks: list[str]
    risk_density: int
    created_at: datetime


class DecisionEnvironmentRepository(BaseRepository[DecisionEnvironmentSnapshot]):
    """Read-only access for environment snapshots.

    Institutional use:
    - Power 'Decision Environment Summary' views.
    - Support IC pre-checks and historical audit.
    """

    async def get_latest_environment_snapshot(self) -> Optional[EnvironmentSnapshotDTO]:
        stmt: Select = (
            select(DecisionEnvironmentSnapshot)
            .order_by(DecisionEnvironmentSnapshot.snapshot_time.desc())
            .limit(1)
        )
        row = (await self._execute(stmt)).scalars().first()
        return _to_snapshot_dto(row) if row else None

    async def get_environment_snapshot_at(self, at_time: datetime) -> Optional[EnvironmentSnapshotDTO]:
        """Get the latest snapshot at or before the provided time."""
        stmt: Select = (
            select(DecisionEnvironmentSnapshot)
            .where(DecisionEnvironmentSnapshot.snapshot_time <= at_time)
            .order_by(DecisionEnvironmentSnapshot.snapshot_time.desc())
            .limit(1)
        )
        row = (await self._execute(stmt)).scalars().first()
        return _to_snapshot_dto(row) if row else None

    async def list_environment_snapshots(
        self, *, start_time: datetime, end_time: datetime, limit: int = 500
    ) -> Sequence[EnvironmentSnapshotDTO]:
        """List snapshots within an inclusive time range, newest-first."""
        stmt: Select = (
            select(DecisionEnvironmentSnapshot)
            .where(DecisionEnvironmentSnapshot.snapshot_time >= start_time)
            .where(DecisionEnvironmentSnapshot.snapshot_time <= end_time)
            .order_by(DecisionEnvironmentSnapshot.snapshot_time.desc())
            .limit(limit)
        )
        rows = (await self._execute(stmt)).scalars().all()
        return [_to_snapshot_dto(r) for r in rows]


def _to_snapshot_dto(m: DecisionEnvironmentSnapshot) -> EnvironmentSnapshotDTO:
    return EnvironmentSnapshotDTO(
        id=str(m.id),
        snapshot_time=m.snapshot_time,
        environment_state=m.environment_state.value,
        dominant_risks=list(m.dominant_risks),
        risk_density=int(m.risk_density),
        created_at=m.created_at,
    )

