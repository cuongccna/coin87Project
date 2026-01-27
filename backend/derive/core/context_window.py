from __future__ import annotations

"""Context window helpers for Job B.

Purpose:
- Fetch only NEW information_events since last cursor.
- Maintain deterministic ordering for processing.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.information_event import InformationEvent


UTC = timezone.utc


@dataclass(frozen=True, slots=True)
class Cursor:
    last_observed_at: datetime
    last_id: uuid.UUID


def default_cursor() -> Cursor:
    return Cursor(last_observed_at=datetime(1970, 1, 1, tzinfo=UTC), last_id=uuid.UUID(int=0))


def fetch_new_information_events(
    db: Session,
    *,
    cursor: Cursor,
    limit: int = 200,
) -> list[InformationEvent]:
    """Fetch new InformationEvent rows strictly after the cursor."""
    stmt = (
        select(InformationEvent)
        .where(
            or_(
                InformationEvent.observed_at > cursor.last_observed_at,
                and_(
                    InformationEvent.observed_at == cursor.last_observed_at,
                    InformationEvent.id > cursor.last_id,
                ),
            )
        )
        .order_by(InformationEvent.observed_at.asc(), InformationEvent.id.asc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def advance_cursor(cursor: Cursor, ev: InformationEvent) -> Cursor:
    # Normalize to UTC for deterministic cursor persistence.
    dt = ev.observed_at
    if dt.tzinfo is None or dt.utcoffset() is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return Cursor(last_observed_at=dt, last_id=ev.id)

