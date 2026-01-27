"""NarrativeCluster model and narrative_memberships association table.

Institutional rationale:
Narratives are persistent and cyclical. They contaminate discretionary decision
processes over time, so institutions require durable tracking of narrative state
without rewriting history.

Controlled mutability:
- Allowed: status, last_seen_at, saturation_level (±1 per update)
%- Forbidden: theme, first_seen_at, deletion
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    Table,
    event,
    inspect,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.sql.sqltypes import Enum as SAEnum, Text

from app.core.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


UTC = timezone.utc


class NarrativeClusterMutationError(RuntimeError):
    """Raised when an attempt is made to mutate or delete a NarrativeCluster illegally."""


class NarrativeStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FADING = "FADING"
    DORMANT = "DORMANT"


narrative_memberships = Table(
    "narrative_memberships",
    Base.metadata,
    Column(
        "narrative_id",
        UUID(as_uuid=True),
        ForeignKey(
            "narrative_clusters.id",
            name="fk_narrative_memberships_narrative_id",
            ondelete="RESTRICT",
        ),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "decision_risk_event_id",
        UUID(as_uuid=True),
        ForeignKey(
            "decision_risk_events.id",
            name="fk_narrative_memberships_decision_risk_event_id",
            ondelete="RESTRICT",
        ),
        primary_key=True,
        nullable=False,
    ),
)


class NarrativeCluster(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A recurring information narrative tracked over time.

    This is not a headline or a news story. It is a persistent contamination
    mechanism that can reactivate. The cluster is never deleted.
    """

    __tablename__ = "narrative_clusters"

    # Parent Narrative (Phase 6)
    narrative_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("narratives.id"), nullable=True, index=True
    )
    narrative = relationship("app.models.narrative.Narrative", back_populates="clusters")

    theme: Mapped[str] = mapped_column(Text, nullable=False)

    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    saturation_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    status: Mapped[NarrativeStatus] = mapped_column(
        SAEnum(NarrativeStatus, name="narrative_status"),
        nullable=False,
        index=True,
    )

    decision_risk_events: Mapped[list["DecisionRiskEvent"]] = relationship(
        "DecisionRiskEvent",
        secondary=narrative_memberships,
        primaryjoin="NarrativeCluster.id == narrative_memberships.c.narrative_id",
        secondaryjoin="DecisionRiskEvent.id == narrative_memberships.c.decision_risk_event_id",
        cascade="save-update, merge",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "saturation_level >= 1 AND saturation_level <= 5",
            name="ck_narrative_clusters_saturation_range",
        ),
        Index("ix_narrative_clusters_last_seen_at", "last_seen_at"),
    )

    @validates("first_seen_at", "last_seen_at")
    def _validate_utc(self, key: str, value: datetime) -> datetime:
        """Enforce timezone-aware UTC datetimes for audit correctness."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{key} must be timezone-aware (UTC).")
        if value.utcoffset() != timedelta(0):
            raise ValueError(f"{key} must be UTC (offset 0).")
        return value.astimezone(UTC)


_ALLOWED_MUTABLE_FIELDS = {"status", "last_seen_at", "saturation_level"}
_FORBIDDEN_MUTABLE_FIELDS = {"theme", "first_seen_at"}


@event.listens_for(NarrativeCluster, "before_update", propagate=True)
def _narrative_cluster_controlled_mutability(mapper, connection, target) -> None:
    state = inspect(target)
    if not state.persistent:
        return

    # Reject forbidden field changes.
    for attr_name in _FORBIDDEN_MUTABLE_FIELDS:
        if state.attrs[attr_name].history.has_changes():
            raise NarrativeClusterMutationError(
                f"NarrativeCluster mutation forbidden: field '{attr_name}' cannot be updated."
            )

    # Reject any other unexpected changes (besides allowed mutable fields).
    changed = {a.key for a in state.attrs if a.history.has_changes()}
    unexpected = changed - _ALLOWED_MUTABLE_FIELDS
    if unexpected:
        raise NarrativeClusterMutationError(
            "NarrativeCluster mutation forbidden: unexpected field update(s): "
            + ", ".join(sorted(unexpected))
        )

    # Enforce saturation_level step changes of at most ±1 per update.
    sat_hist = state.attrs["saturation_level"].history
    if sat_hist.has_changes():
        old = sat_hist.deleted[0] if sat_hist.deleted else None
        new = sat_hist.added[0] if sat_hist.added else None
        if old is None or new is None:
            raise NarrativeClusterMutationError(
                "NarrativeCluster mutation invalid: saturation_level change could not be validated."
            )
        if abs(int(new) - int(old)) != 1:
            raise NarrativeClusterMutationError(
                "NarrativeCluster mutation forbidden: saturation_level may change only by +1 or -1 per update."
            )


@event.listens_for(NarrativeCluster, "before_delete", propagate=True)
def _narrative_cluster_prevent_delete(mapper, connection, target) -> None:
    raise NarrativeClusterMutationError(
        "NarrativeCluster deletion is forbidden. Narratives persist for institutional memory."
    )

