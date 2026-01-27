"""DecisionImpactRecord model.

Institutional rationale:
DecisionImpactRecord captures post-decision reflection for governance and
discipline. It is not performance attribution. Records are immutable to prevent
retroactive rewriting; corrections are appended as new records linked to the same
DecisionContext.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, event, inspect
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.sql.sqltypes import Text

from app.core.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.decision_context import DecisionContext


UTC = timezone.utc


class DecisionImpactImmutabilityError(RuntimeError):
    """Raised when an attempt is made to mutate or delete a DecisionImpactRecord."""


class DecisionImpactRecord(UUIDPrimaryKeyMixin, Base):
    """Immutable post-decision reflection record."""

    __tablename__ = "decision_impact_records"

    decision_context_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "decision_contexts.id",
            name="fk_decision_impact_records_decision_context_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    environment_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "decision_environment_snapshots.id",
            name="fk_decision_impact_records_environment_snapshot_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    qualitative_outcome: Mapped[str] = mapped_column(Text, nullable=False)

    learning_flags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Read-only relationship from this side.
    decision_context: Mapped["DecisionContext"] = relationship(
        "DecisionContext",
        primaryjoin="DecisionImpactRecord.decision_context_id == DecisionContext.id",
        viewonly=True,
    )

    __table_args__ = (Index("ix_decision_impact_records_decision_context_id", "decision_context_id"),)

    @validates("recorded_at")
    def _validate_utc(self, key: str, value: datetime) -> datetime:
        """Enforce timezone-aware UTC datetimes for audit correctness."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{key} must be timezone-aware (UTC).")
        if value.utcoffset() != timedelta(0):
            raise ValueError(f"{key} must be UTC (offset 0).")
        return value.astimezone(UTC)


@event.listens_for(DecisionImpactRecord, "before_update", propagate=True)
def _decision_impact_prevent_updates(mapper, connection, target) -> None:
    state = inspect(target)
    if not state.persistent:
        return

    changed = [a.key for a in state.attrs if a.history.has_changes()]
    if changed:
        raise DecisionImpactImmutabilityError(
            "DecisionImpactRecord is immutable; updates are forbidden (changed: "
            + ", ".join(sorted(changed))
            + "). Create a new DecisionImpactRecord for corrections."
        )


@event.listens_for(DecisionImpactRecord, "before_delete", propagate=True)
def _decision_impact_prevent_delete(mapper, connection, target) -> None:
    raise DecisionImpactImmutabilityError(
        "DecisionImpactRecord deletion is forbidden. Institutional memory records must remain auditable."
    )

