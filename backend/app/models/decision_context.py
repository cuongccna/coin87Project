"""DecisionContext model.

Institutional rationale:
DecisionContext represents a formal decision moment (IC meeting, PM review, or
strategy discussion). These records form institutional memory and must be
auditable. The decision type and time are immutable to prevent rewriting the
historical record. Description is allowed to be clarified only by append-style
updates (additive context), never by changing prior intent.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Index, event, inspect
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.sql.sqltypes import Enum as SAEnum, Text

from app.core.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


UTC = timezone.utc


class DecisionContextMutationError(RuntimeError):
    """Raised when an attempt is made to mutate or delete a DecisionContext illegally."""


class DecisionContextType(str, Enum):
    IC_MEETING = "IC_MEETING"
    PM_REVIEW = "PM_REVIEW"
    ALLOCATION_DECISION = "ALLOCATION_DECISION"
    STRATEGY_REVIEW = "STRATEGY_REVIEW"


class DecisionContext(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Formal decision moment for institutional governance."""

    __tablename__ = "decision_contexts"

    context_type: Mapped[DecisionContextType] = mapped_column(
        SAEnum(DecisionContextType, name="decision_context_type"),
        nullable=False,
    )

    context_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    impact_records: Mapped[list["DecisionImpactRecord"]] = relationship(
        "DecisionImpactRecord",
        back_populates=None,
        cascade="save-update, merge",
        passive_deletes=True,
    )

    __table_args__ = (Index("ix_decision_contexts_context_time", "context_time"),)

    @validates("context_time")
    def _validate_utc(self, key: str, value: datetime) -> datetime:
        """Enforce timezone-aware UTC datetimes for audit correctness."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{key} must be timezone-aware (UTC).")
        if value.utcoffset() != timedelta(0):
            raise ValueError(f"{key} must be UTC (offset 0).")
        return value.astimezone(UTC)


@event.listens_for(DecisionContext, "before_update", propagate=True)
def _decision_context_controlled_mutability(mapper, connection, target) -> None:
    """Allow only additive clarification to description; forbid rewriting core fields."""
    state = inspect(target)
    if not state.persistent:
        return

    # Forbid changes to core immutable fields.
    if state.attrs["context_type"].history.has_changes():
        raise DecisionContextMutationError(
            "DecisionContext is immutable: context_type cannot be updated."
        )
    if state.attrs["context_time"].history.has_changes():
        raise DecisionContextMutationError(
            "DecisionContext is immutable: context_time cannot be updated."
        )

    # description may change only by append-style clarification.
    desc_hist = state.attrs["description"].history
    if desc_hist.has_changes():
        old = desc_hist.deleted[0] if desc_hist.deleted else None
        new = desc_hist.added[0] if desc_hist.added else None

        if new is None:
            raise DecisionContextMutationError(
                "DecisionContext description cannot be cleared; only additive clarification is allowed."
            )
        if old is None:
            # first-time description addition is allowed.
            return
        if not isinstance(old, str) or not isinstance(new, str):
            raise DecisionContextMutationError(
                "DecisionContext description update could not be validated."
            )
        if len(new) < len(old) or not new.startswith(old):
            raise DecisionContextMutationError(
                "DecisionContext description may only be extended (append-only clarification). "
                "Rewriting prior intent is forbidden."
            )

    # Reject any other unexpected changes.
    changed = {a.key for a in state.attrs if a.history.has_changes()}
    allowed = {"description"}  # core fields handled above (changes already blocked)
    unexpected = changed - allowed
    if unexpected:
        raise DecisionContextMutationError(
            "DecisionContext mutation forbidden: unexpected field update(s): "
            + ", ".join(sorted(unexpected))
        )


@event.listens_for(DecisionContext, "before_delete", propagate=True)
def _decision_context_prevent_delete(mapper, connection, target) -> None:
    raise DecisionContextMutationError(
        "DecisionContext deletion is forbidden. Institutional memory records must remain auditable."
    )

