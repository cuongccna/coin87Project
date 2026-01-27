"""ConsensusPressureEvent model.

Institutional rationale:
ConsensusPressureEvent captures non-price pressure that can push discretionary
PMs/ICs to act due to perceived consensus (media saturation, analyst alignment,
social unanimity, reputational optics). These records must be immutable:
pressure changes over time are represented as new events, preserving an auditable
timeline of decision pressure conditions.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    event,
    inspect,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.sql.sqltypes import Text

from app.core.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.narrative_cluster import NarrativeCluster


UTC = timezone.utc


class ConsensusPressureImmutabilityError(RuntimeError):
    """Raised when an attempt is made to mutate or delete a ConsensusPressureEvent."""


class ConsensusPressureEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Immutable event representing perceived consensus pressure."""

    __tablename__ = "consensus_pressure_events"

    narrative_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "narrative_clusters.id",
            name="fk_consensus_pressure_events_narrative_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    pressure_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    dominant_sources: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
    )

    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Read-only relationship from this side: association is set via FK only.
    narrative: Mapped["NarrativeCluster"] = relationship(
        "NarrativeCluster",
        primaryjoin="ConsensusPressureEvent.narrative_id == NarrativeCluster.id",
        viewonly=True,
    )

    __table_args__ = (
        CheckConstraint(
            "pressure_level >= 1 AND pressure_level <= 5",
            name="ck_consensus_pressure_events_pressure_range",
        ),
        Index("ix_consensus_pressure_events_detected_at", "detected_at"),
    )

    @validates("detected_at")
    def _validate_utc(self, key: str, value: datetime) -> datetime:
        """Enforce timezone-aware UTC datetimes for audit correctness."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{key} must be timezone-aware (UTC).")
        if value.utcoffset() != timedelta(0):
            raise ValueError(f"{key} must be UTC (offset 0).")
        return value.astimezone(UTC)


_IMMUTABLE_FIELDS = ("narrative_id", "pressure_level", "dominant_sources", "detected_at")


@event.listens_for(ConsensusPressureEvent, "before_update", propagate=True)
def _consensus_pressure_prevent_updates(mapper, connection, target) -> None:
    state = inspect(target)
    if not state.persistent:
        return

    for attr_name in _IMMUTABLE_FIELDS:
        if state.attrs[attr_name].history.has_changes():
            raise ConsensusPressureImmutabilityError(
                f"ConsensusPressureEvent is immutable: field '{attr_name}' cannot be updated. "
                "Create a new ConsensusPressureEvent for updated pressure conditions."
            )


@event.listens_for(ConsensusPressureEvent, "before_delete", propagate=True)
def _consensus_pressure_prevent_delete(mapper, connection, target) -> None:
    raise ConsensusPressureImmutabilityError(
        "ConsensusPressureEvent deletion is forbidden. "
        "Historical pressure records must remain immutable for auditability."
    )

