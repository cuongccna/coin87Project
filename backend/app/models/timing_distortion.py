"""TimingDistortionWindow model.

Institutional rationale:
TimingDistortionWindow represents a time interval where information induces
systematic timing errors for discretionary decisions (late or premature action).

This is not a price-timing construct. It is an auditable governance artifact:
if understanding changes, a new window must be appended rather than rewriting
the historical record.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    event,
    inspect,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.sql.sqltypes import Enum as SAEnum

from app.core.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.decision_risk_event import DecisionRiskEvent


UTC = timezone.utc


class TimingDistortionImmutabilityError(RuntimeError):
    """Raised when an attempt is made to mutate or delete a TimingDistortionWindow."""


class DistortionType(str, Enum):
    LATE_ACTION = "LATE_ACTION"
    PREMATURE_ACTION = "PREMATURE_ACTION"


class TimingDistortionWindow(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Immutable time window describing information-induced timing distortion."""

    __tablename__ = "timing_distortion_windows"

    decision_risk_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "decision_risk_events.id",
            name="fk_timing_distortion_windows_decision_risk_event_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    distortion_type: Mapped[DistortionType] = mapped_column(
        SAEnum(DistortionType, name="timing_distortion_type"),
        nullable=False,
    )

    # Read-only relationship from this side: association is set via FK only.
    decision_risk_event: Mapped["DecisionRiskEvent"] = relationship(
        "DecisionRiskEvent",
        primaryjoin="TimingDistortionWindow.decision_risk_event_id == DecisionRiskEvent.id",
        viewonly=True,
    )

    __table_args__ = (
        CheckConstraint(
            "window_end > window_start",
            name="ck_timing_distortion_windows_end_after_start",
        ),
        Index("ix_timing_distortion_windows_range", "window_start", "window_end"),
    )

    @validates("window_start", "window_end")
    def _validate_utc(self, key: str, value: datetime) -> datetime:
        """Enforce timezone-aware UTC datetimes for audit correctness."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{key} must be timezone-aware (UTC).")
        if value.utcoffset() != timedelta(0):
            raise ValueError(f"{key} must be UTC (offset 0).")
        return value.astimezone(UTC)


_IMMUTABLE_FIELDS = ("decision_risk_event_id", "window_start", "window_end", "distortion_type")


@event.listens_for(TimingDistortionWindow, "before_update", propagate=True)
def _timing_distortion_prevent_updates(mapper, connection, target) -> None:
    state = inspect(target)
    if not state.persistent:
        return

    for attr_name in _IMMUTABLE_FIELDS:
        if state.attrs[attr_name].history.has_changes():
            raise TimingDistortionImmutabilityError(
                f"TimingDistortionWindow is immutable: field '{attr_name}' cannot be updated. "
                "Create a new TimingDistortionWindow for revised understanding."
            )


@event.listens_for(TimingDistortionWindow, "before_delete", propagate=True)
def _timing_distortion_prevent_delete(mapper, connection, target) -> None:
    raise TimingDistortionImmutabilityError(
        "TimingDistortionWindow deletion is forbidden. "
        "Historical timing distortion windows must remain immutable for auditability."
    )

