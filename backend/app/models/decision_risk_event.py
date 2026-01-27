"""DecisionRiskEvent model.

Institutional rationale:
DecisionRiskEvent is the core value object of coin87. It represents the moment
when an information input becomes dangerous for discretionary decision-making.

Immutability is mandatory because:
- Investment committees rely on stable, auditable historical records.
- Re-evaluation must append new records; rewriting risk history destroys trust.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    event,
    inspect,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.sql.sqltypes import Enum as SAEnum, Text

from app.core.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.information_event import InformationEvent


UTC = timezone.utc


class DecisionRiskImmutabilityError(RuntimeError):
    """Raised when an attempt is made to mutate or delete a DecisionRiskEvent."""


class RiskType(str, Enum):
    TIMING_DISTORTION = "TIMING_DISTORTION"
    NARRATIVE_CONTAMINATION = "NARRATIVE_CONTAMINATION"
    CONSENSUS_TRAP = "CONSENSUS_TRAP"
    STRUCTURAL_DECISION_RISK = "STRUCTURAL_DECISION_RISK"


class RecommendedPosture(str, Enum):
    IGNORE = "IGNORE"
    REVIEW = "REVIEW"
    DELAY = "DELAY"


class DecisionRiskEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Append-only risk object derived from information inputs.

    Allowed mutation: only `valid_to` may be set/updated to close out a risk
    window. All other fields are immutable after insert.
    """

    __tablename__ = "decision_risk_events"

    information_event_id: Mapped["uuid.UUID"] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "information_events.id",
            name="fk_decision_risk_events_information_event_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    risk_type: Mapped[RiskType] = mapped_column(
        SAEnum(RiskType, name="decision_risk_type"),
        nullable=False,
    )

    severity: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    affected_decisions: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
    )

    recommended_posture: Mapped[RecommendedPosture] = mapped_column(
        SAEnum(RecommendedPosture, name="decision_recommended_posture"),
        nullable=False,
    )

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    valid_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Read-only relationship from this side: association is set via FK only.
    information_event: Mapped["InformationEvent"] = relationship(
        "InformationEvent",
        primaryjoin="DecisionRiskEvent.information_event_id == InformationEvent.id",
        viewonly=True,
    )

    __table_args__ = (
        CheckConstraint(
            "severity >= 1 AND severity <= 5",
            name="ck_decision_risk_events_severity_range",
        ),
        CheckConstraint(
            "(valid_to IS NULL) OR (valid_to > valid_from)",
            name="ck_decision_risk_events_valid_to_after_valid_from",
        ),
        Index("ix_decision_risk_events_valid_range", "valid_from", "valid_to"),
    )

    @validates("detected_at", "valid_from", "valid_to")
    def _validate_utc(self, key: str, value: Optional[datetime]) -> Optional[datetime]:
        """Enforce timezone-aware UTC datetimes for audit correctness."""
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{key} must be timezone-aware (UTC).")
        if value.utcoffset() != timedelta(0):
            raise ValueError(f"{key} must be UTC (offset 0).")
        return value.astimezone(UTC)


_IMMUTABLE_FIELDS = (
    "risk_type",
    "severity",
    "affected_decisions",
    "recommended_posture",
    "detected_at",
    "valid_from",
)


@event.listens_for(DecisionRiskEvent, "before_update", propagate=True)
def _decision_risk_event_prevent_forbidden_updates(mapper, connection, target) -> None:
    """Reject any update to immutable fields after insert."""
    state = inspect(target)
    if not state.persistent:
        return

    for attr_name in _IMMUTABLE_FIELDS:
        hist = state.attrs[attr_name].history
        if hist.has_changes():
            raise DecisionRiskImmutabilityError(
                f"DecisionRiskEvent is immutable: field '{attr_name}' cannot be updated. "
                "Create a new DecisionRiskEvent for re-evaluation."
            )


@event.listens_for(DecisionRiskEvent, "before_delete", propagate=True)
def _decision_risk_event_prevent_delete(mapper, connection, target) -> None:
    """Reject deletes to preserve institutional audit trails."""
    raise DecisionRiskImmutabilityError(
        "DecisionRiskEvent deletion is forbidden. "
        "Historical decision risk records must remain immutable for auditability."
    )

