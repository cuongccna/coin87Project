"""ClusterVisibility model (Phase 7).

Determines the visibility and ranking priority of information clusters 
based on their noise characteristics.

Levels:
- NONE: Fully visible, normal ranking.
- DEPRIORITIZE: Visible but ranked low (e.g. low reliability).
- SUPPRESS: Hidden from main views (e.g. pure noise, spam, single-source hallucinations).

Coin87 Philosophy:
- Noise Suppression is not Censorship.
- It is quality filtering based on BEHAVIOR over time.
- Reasons must be explicit.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, UpdatedAtMixin


UTC = timezone.utc


class SuppressLevel(str, enum.Enum):
    NONE = "NONE"
    DEPRIORITIZE = "DEPRIORITIZE"
    SUPPRESS = "SUPPRESS"


class ClusterVisibility(Base, UpdatedAtMixin):
    """Visibility state for a NarrativeCluster."""
    
    __tablename__ = "cluster_visibility"
    
    # One-to-One with NarrativeCluster
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("narrative_clusters.id", ondelete="CASCADE"), 
        primary_key=True
    )
    
    suppress_level: Mapped[SuppressLevel] = mapped_column(
        Enum(SuppressLevel), 
        nullable=False, 
        default=SuppressLevel.NONE
    )
    
    reason_code: Mapped[str] = mapped_column(String, nullable=False, default="INIT")
    reason_description: Mapped[str] = mapped_column(Text, nullable=True)
    
    last_evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now()
    )
