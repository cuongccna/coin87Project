"""SQLAlchemy model for InformationEventEnrichment."""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.models.information_event import Base


class InformationEventEnrichment(Base):
    """
    AI-enriched analysis cho InformationEvents.
    
    Triết lý:
    - InformationEvent = raw, immutable input
    - InformationEventEnrichment = derived, AI-analyzed data
    - Separate table để maintain audit trail và cho phép re-processing
    """
    __tablename__ = "information_event_enrichment"
    __table_args__ = (
        Index("idx_enrichment_event_id", "information_event_id"),
        Index("idx_enrichment_sentiment", "sentiment"),
        Index("idx_enrichment_category", "category"),
        Index("idx_enrichment_score", "worth_click_score"),
        Index("idx_enrichment_generated_at", "generated_at"),
        UniqueConstraint("information_event_id", name="uq_enrichment_event"),
        {"comment": "AI-enriched analysis for InformationEvents (derived data, separate from immutable raw input)"}
    )

    id = Column(Integer, primary_key=True)
    information_event_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("information_events.id", ondelete="CASCADE"),
        nullable=False,
        comment="FK to information_events"
    )

    # AI Analysis Results
    ai_summary = Column(
        String(500),
        nullable=True,
        comment="AI-generated summary (max 500 chars)"
    )
    entities = Column(
        JSONB,
        nullable=True,
        comment="Extracted entities (tokens, protocols, people, orgs)"
    )
    sentiment = Column(
        String(20),
        nullable=True,
        comment="bullish|bearish|neutral"
    )
    confidence = Column(
        Float,
        nullable=True,
        comment="AI confidence score 0.0-1.0"
    )
    keywords = Column(
        JSONB,
        nullable=True,
        comment="Extracted keywords"
    )
    category = Column(
        String(50),
        nullable=True,
        comment="Content category: regulation|technology|market|security|other"
    )

    narrative_analysis = Column(
        JSONB,
        nullable=True,
        comment="Advanced analysis: expected_mechanism, invalidation_signal, trapped_persona"
    )

    # Worth-Click Scoring
    worth_click_score = Column(
        Float,
        nullable=True,
        comment="Score from worth-click scorer (0-10)"
    )
    worth_click_breakdown = Column(
        JSONB,
        nullable=True,
        comment="Scoring breakdown details"
    )

    # Pre-Filter Decision
    filter_decision = Column(
        String(50),
        nullable=True,
        comment="Pre-filter decision: pass|reject_*"
    )

    # Timestamps
    generated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When enrichment was generated"
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Last update timestamp"
    )

    # Relationships
    # information_event = relationship("InformationEvent", back_populates="enrichment")

    def __repr__(self) -> str:
        return (
            f"<InformationEventEnrichment(id={self.id}, "
            f"event_id={self.information_event_id}, "
            f"sentiment={self.sentiment}, "
            f"score={self.worth_click_score})>"
        )
