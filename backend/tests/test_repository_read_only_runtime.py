from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.repositories.base import BaseRepository, RepositoryReadOnlyViolation
from app.models.decision_environment_snapshot import DecisionEnvironmentSnapshot
from app.models.decision_environment_snapshot import EnvironmentState


def test_repository_rejects_dirty_session(db_session: Session):
    snap = DecisionEnvironmentSnapshot(
        snapshot_time=datetime.now(tz=timezone.utc),
        environment_state=EnvironmentState.CLEAN,
        dominant_risks=[],
        risk_density=0,
    )
    db_session.add(snap)

    repo: BaseRepository[DecisionEnvironmentSnapshot] = BaseRepository(db_session)
    with pytest.raises(RepositoryReadOnlyViolation):
        asyncio.run(repo._execute(select(DecisionEnvironmentSnapshot)))


def test_repository_rejects_non_select(db_session: Session):
    repo: BaseRepository[DecisionEnvironmentSnapshot] = BaseRepository(db_session)
    with pytest.raises(RepositoryReadOnlyViolation):
        asyncio.run(repo._execute(insert(DecisionEnvironmentSnapshot)))

