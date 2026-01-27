"""Audit Trace model (Phase 9).

Records the "WHY" behind automated and human decisions.
Strictly limited to qualitative explanations to maintain trust without noise.

Rules:
- Append-only.
- Recorded only on state changes.
- Factors are qualitative (High/Med/Low), not quantitative.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, CreatedAtMixin


UTC = timezone.utc


class AuditDecisionType(str, enum.Enum):
    RELIABILITY_CLASSIFICATION = "RELIABILITY_CLASSIFICATION"
    NOISE_SUPPRESSION = "NOISE_SUPPRESSION"
    NARRATIVE_STATE = "NARRATIVE_STATE"
    EDITORIAL_REVIEW = "EDITORIAL_REVIEW"


class AuditTrace(Base, CreatedAtMixin):
    """Immutable record of a decision event for a specific cluster."""
    
    __tablename__ = "audit_traces"
    
    trace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    # Linked to Cluster
    cluster_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("narrative_clusters.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    decision_type: Mapped[AuditDecisionType] = mapped_column(
        Enum(AuditDecisionType), nullable=False
    )
    
    # Human-readable summary (1-2 sentences)
    decision_summary: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Qualitative factors (JSON)
    # e.g. {"source_diversity": "HIGH", "contradictions": "NONE"}
    factors: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})

    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
