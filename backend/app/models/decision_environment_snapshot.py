"""DecisionEnvironmentSnapshot model.

Institutional rationale:
DecisionEnvironmentSnapshot captures the state of the information environment at
an instant in time. It is an immutable governance artifact used for IC packets,
post-mortems, and audit trails. If understanding changes, new snapshots must be
created; historical snapshots are never rewritten or deleted.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, Index, SmallInteger, event, inspect
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, validates
from sqlalchemy.sql.sqltypes import Enum as SAEnum, Text

from app.core.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


UTC = timezone.utc


class DecisionEnvironmentSnapshotImmutabilityError(RuntimeError):
    """Raised when an attempt is made to mutate or delete a DecisionEnvironmentSnapshot."""


class EnvironmentState(str, Enum):
    CLEAN = "CLEAN"
    CAUTION = "CAUTION"
    CONTAMINATED = "CONTAMINATED"


class DecisionEnvironmentSnapshot(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Immutable snapshot of decision environment state."""

    __tablename__ = "decision_environment_snapshots"

    snapshot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    environment_state: Mapped[EnvironmentState] = mapped_column(
        SAEnum(EnvironmentState, name="decision_environment_state"),
        nullable=False,
    )

    dominant_risks: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)

    risk_density: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    __table_args__ = (
        CheckConstraint("risk_density >= 0", name="ck_decision_environment_snapshots_risk_density_nonneg"),
        Index("ix_decision_environment_snapshots_snapshot_time", "snapshot_time"),
    )

    @validates("snapshot_time")
    def _validate_utc(self, key: str, value: datetime) -> datetime:
        """Enforce timezone-aware UTC datetimes for audit correctness."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{key} must be timezone-aware (UTC).")
        if value.utcoffset() != timedelta(0):
            raise ValueError(f"{key} must be UTC (offset 0).")
        return value.astimezone(UTC)


@event.listens_for(DecisionEnvironmentSnapshot, "before_update", propagate=True)
def _decision_environment_snapshot_prevent_updates(mapper, connection, target) -> None:
    state = inspect(target)
    if not state.persistent:
        return

    changed = [a.key for a in state.attrs if a.history.has_changes()]
    if changed:
        raise DecisionEnvironmentSnapshotImmutabilityError(
            "DecisionEnvironmentSnapshot is immutable; updates are forbidden (changed: "
            + ", ".join(sorted(changed))
            + "). Create a new snapshot at a later time."
        )


@event.listens_for(DecisionEnvironmentSnapshot, "before_delete", propagate=True)
def _decision_environment_snapshot_prevent_delete(mapper, connection, target) -> None:
    raise DecisionEnvironmentSnapshotImmutabilityError(
        "DecisionEnvironmentSnapshot deletion is forbidden. Snapshots must remain immutable for auditability."
    )

