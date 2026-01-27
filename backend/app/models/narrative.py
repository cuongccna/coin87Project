"""Narrative model (Phase 6).

Represents the high-level lifecycle of an information theme.
Distinct from NarrativeCluster (which is the data container), the Narrative
tracks the *evolutionary state* of the story.

States:
- EMERGING: Developing, low confidence/volume.
- ACTIVE: High volume, high velocity.
- SATURATED: High volume, but plateaued velocity.
- FADING: Declining velocity.
- DORMANT: Inactive.

Coin87 Philosophy:
- Tracks presence/absence and intensity.
- NO market sentiment.
- NO price prediction.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, CreatedAtMixin, UpdatedAtMixin


UTC = timezone.utc


class NarrativeState(str, enum.Enum):
    EMERGING = "EMERGING"
    ACTIVE = "ACTIVE"
    SATURATED = "SATURATED"
    FADING = "FADING"
    DORMANT = "DORMANT"


class Narrative(Base, CreatedAtMixin, UpdatedAtMixin):
    """The lifecycle container for a thematic information thread."""
    
    __tablename__ = "narratives"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    # The topic/theme (usually 1:1 with the primary Cluster's theme)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    
    # State Machine
    current_state: Mapped[NarrativeState] = mapped_column(
        Enum(NarrativeState), nullable=False, default=NarrativeState.EMERGING
    )
    
    # Lifecycle Timestamps
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Relationship to clusters (One Narrative -> Many Clusters, though often 1:1)
    # We will need to update NarrativeCluster to have narrative_id
    clusters = relationship("NarrativeCluster", back_populates="narrative")
    
    # Metrics history
    metrics_history = relationship("NarrativeMetrics", back_populates="narrative")


class NarrativeMetrics(Base, CreatedAtMixin):
    """Point-in-time snapshot of narrative lifecycle metrics."""
    
    __tablename__ = "narrative_metrics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    narrative_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("narratives.id"), nullable=False, index=True
    )
    
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
    
    # Metrics
    mention_velocity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0) # mentions/hour
    active_duration_minutes: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_state: Mapped[NarrativeState] = mapped_column(Enum(NarrativeState), nullable=False)
    
    narrative = relationship("Narrative", back_populates="metrics_history")
