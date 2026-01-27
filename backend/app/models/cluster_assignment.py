"""ClusterAssignment model.

Directly links a raw InformationEvent to a NarrativeCluster.
Enforces 1:1 relationship (one event -> one cluster).

Coin87 Philosophy:
- Information Reliability Tracking
- Raw events are immutable
- Clusters evolve over time
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, CreatedAtMixin


UTC = timezone.utc


class ClusterAssignment(CreatedAtMixin, Base):
    """Link between a raw InformationEvent and its assigned NarrativeCluster."""
    
    __tablename__ = "cluster_assignments"
    
    # Primary Key is the event ID itself (One-to-One / Many-to-One enforcement)
    # An event can only belong to ONE cluster.
    information_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "information_events.id", 
            name="fk_cluster_assignments_information_event_id",
            ondelete="CASCADE" # If event is deleted (rare), assignment goes too
        ),
        primary_key=True,
    )

    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "narrative_clusters.id",
            name="fk_cluster_assignments_cluster_id",
            ondelete="RESTRICT" # Prevent deleting cluster if it has assignments
        ),
        nullable=False,
        index=True,
    )
    
    confidence_score: Mapped[float] = mapped_column(nullable=False, default=1.0)
    is_manual_override: Mapped[bool] = mapped_column(nullable=False, default=False)
    
    # Relationships (optional, for navigation if needed)
    # event: Mapped["InformationEvent"] = relationship(...)
    # cluster: Mapped["NarrativeCluster"] = relationship(...)
