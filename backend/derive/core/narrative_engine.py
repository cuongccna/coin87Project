from __future__ import annotations

"""Narrative engine (Job B).

Responsibilities:
- Create/lookup long-lived NarrativeCluster by deterministic theme (from rules).
- Controlled updates only: last_seen_at, saturation_level (+1 only), status.
- Append-only narrative_memberships linking narrative <-> decision_risk_event.
- If rules version changes, log re_evaluation_logs for forward-only reinterpretation.

STRICT:
- Never delete anything.
- Never rename narratives silently (theme is immutable).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.narrative_cluster import NarrativeCluster, NarrativeStatus, narrative_memberships
from app.models.re_evaluation_log import ReEvaluationLog


UTC = timezone.utc


@dataclass(frozen=True, slots=True)
class NarrativeResult:
    narrative_id: uuid.UUID
    created: bool
    updated: bool


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


def get_or_create_cluster(
    db: Session,
    *,
    theme: str,
    seen_at: datetime,
    rules_version: str,
    prev_rules_version: Optional[str],
) -> tuple[NarrativeCluster, bool, Optional[ReEvaluationLog]]:
    """Get or create NarrativeCluster by immutable theme."""
    theme = theme.strip()
    stmt = select(NarrativeCluster).where(NarrativeCluster.theme == theme)
    existing = db.execute(stmt).scalars().first()

    if existing is None:
        cluster = NarrativeCluster(
            theme=theme,
            first_seen_at=seen_at,
            last_seen_at=seen_at,
            saturation_level=1,
            status=NarrativeStatus.ACTIVE,
        )
        db.add(cluster)
        db.flush()
        return cluster, True, None

    # Controlled updates: last_seen_at, saturation_level (+1 only), status.
    before = {
        "status": str(existing.status),
        "last_seen_at": existing.last_seen_at.isoformat(),
        "saturation_level": int(existing.saturation_level),
    }

    updated = False
    # last_seen_at monotonic forward
    if seen_at > existing.last_seen_at:
        existing.last_seen_at = seen_at
        updated = True
    if existing.status != NarrativeStatus.ACTIVE:
        existing.status = NarrativeStatus.ACTIVE
        updated = True
    # saturation step (+1 only, capped; if capped, do not change to avoid violating ±1 constraint)
    if existing.saturation_level < 5:
        existing.saturation_level = int(existing.saturation_level) + 1
        updated = True

    reeval: Optional[ReEvaluationLog] = None
    # Re-evaluation log on rules version change (forward-only reinterpretation signal).
    if prev_rules_version and prev_rules_version != rules_version and updated:
        after = {
            "status": str(existing.status),
            "last_seen_at": existing.last_seen_at.isoformat(),
            "saturation_level": int(existing.saturation_level),
        }
        reeval = ReEvaluationLog(
            entity_type="narrative_clusters",
            entity_id=existing.id,
            previous_state=before,
            new_state=after,
            reason=f"rules_version_changed {prev_rules_version} -> {rules_version}",
        )
        db.add(reeval)

    return existing, False, reeval


def attach_membership(
    db: Session,
    *,
    narrative_id: uuid.UUID,
    decision_risk_event_id: uuid.UUID,
) -> bool:
    """Append-only insert into narrative_memberships; ignore duplicates."""
    stmt = (
        pg_insert(narrative_memberships)
        .values(narrative_id=narrative_id, decision_risk_event_id=decision_risk_event_id)
        .on_conflict_do_nothing()
    )
    res = db.execute(stmt)
    return bool(getattr(res, "rowcount", 0))

