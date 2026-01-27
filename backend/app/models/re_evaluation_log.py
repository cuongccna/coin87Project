"""ReEvaluationLog model.

Institutional rationale:
ReEvaluationLog is the safe mechanism to admit reinterpretation without
falsifying history. It records an additive audit trail showing previous vs new
interpretation states, the reason, and the time of re-evaluation. Entries are
immutable and never deleted.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, ForeignKey, Index, event, func, inspect
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, validates
from sqlalchemy.sql.sqltypes import Text

from app.core.base import Base, UUIDPrimaryKeyMixin


UTC = timezone.utc


class ReEvaluationLogImmutabilityError(RuntimeError):
    """Raised when an attempt is made to mutate or delete a ReEvaluationLog."""


class ReEvaluationLog(UUIDPrimaryKeyMixin, Base):
    """Immutable re-evaluation audit record."""

    __tablename__ = "re_evaluation_logs"

    entity_type: Mapped[str] = mapped_column(Text, nullable=False)

    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    previous_state: Mapped[dict] = mapped_column(JSONB, nullable=False)

    new_state: Mapped[dict] = mapped_column(JSONB, nullable=False)

    reason: Mapped[str] = mapped_column(Text, nullable=False)

    re_evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_re_evaluation_logs_entity", "entity_type", "entity_id"),
        Index("ix_re_evaluation_logs_re_evaluated_at", "re_evaluated_at"),
    )

    @validates("re_evaluated_at")
    def _validate_utc(self, key: str, value: datetime) -> datetime:
        """Enforce timezone-aware UTC datetimes for audit correctness."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{key} must be timezone-aware (UTC).")
        if value.utcoffset() != timedelta(0):
            raise ValueError(f"{key} must be UTC (offset 0).")
        return value.astimezone(UTC)


@event.listens_for(ReEvaluationLog, "before_update", propagate=True)
def _re_evaluation_log_prevent_updates(mapper, connection, target) -> None:
    state = inspect(target)
    if not state.persistent:
        return

    changed = [a.key for a in state.attrs if a.history.has_changes()]
    if changed:
        raise ReEvaluationLogImmutabilityError(
            "ReEvaluationLog is immutable; updates are forbidden (changed: "
            + ", ".join(sorted(changed))
            + "). Re-evaluation is always additive."
        )


@event.listens_for(ReEvaluationLog, "before_delete", propagate=True)
def _re_evaluation_log_prevent_delete(mapper, connection, target) -> None:
    raise ReEvaluationLogImmutabilityError(
        "ReEvaluationLog deletion is forbidden. Re-evaluation history must remain immutable for auditability."
    )

