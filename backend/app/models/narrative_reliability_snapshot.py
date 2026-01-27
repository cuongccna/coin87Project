"""NarrativeReliabilitySnapshot model.

Stores point-in-time reliability assessments for NarrativeClusters.
Append-only history to support trend analysis and audit.

Coin87 Philosophy:
- Track reliability evolution over time
- Never overwrite history
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import Enum as SAEnum

from app.core.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from derive.core.reliability import ReliabilityStatus


UTC = timezone.utc


class NarrativeReliabilitySnapshot(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Immutable snapshot of a cluster's reliability state at a specific time."""

    __tablename__ = "narrative_reliability_snapshots"

    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "narrative_clusters.id",
            name="fk_narrative_reliability_snapshots_cluster_id",
            ondelete="CASCADE",  # If cluster is gone, history is less relevant, but usually we don't delete clusters.
        ),
        nullable=False,
        index=True,
    )

    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    reliability_status: Mapped[ReliabilityStatus] = mapped_column(
        SAEnum(ReliabilityStatus, name="reliability_status", create_type=False),
         # create_type=False assumes the enum type might be shared or created elsewhere. 
         # But usually in simple setup we let SA create it. 
         # Given ReliabilityStatus is defined in python code, we map it here.
         # Ideally we should define the Enum type schema if shared.
        nullable=False,
    )

    reliability_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # Store the raw metrics that led to this score for future analysis/re-scoring
    metrics_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    
    # Store reasoning for explainability
    reasoning_snapshot: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list
    )

    __table_args__ = (
        Index(
            "ix_narrative_reliability_snapshots_cluster_time",
            "cluster_id",
            "snapshot_at",
        ),
    )
