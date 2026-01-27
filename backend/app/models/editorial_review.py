"""Editorial Review Model (Phase 8).

Minimal human-in-the-loop layer for resolving system ambiguity.
Maintains the 'Clean Hands' philosophy of Coin87:
- Humans do not create content.
- Humans do not rank content.
- Humans only RESOLVE uncertainty flagged by the system.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, CreatedAtMixin


UTC = timezone.utc


class EditorialAction(str, enum.Enum):
    CONFIRM_AUTOMATION = "CONFIRM_AUTOMATION"          # System was right
    FLAG_AMBIGUOUS = "FLAG_AMBIGUOUS"                  # System was unclear, but human is also unsure (do nothing)
    REQUEST_REEVALUATION = "REQUEST_REEVALUATION"      # System input seems wrong, re-run derivation potentially


class ReviewTriggerReason(str, enum.Enum):
    WEAK_ACTIVE_NARRATIVE = "WEAK_ACTIVE_NARRATIVE"
    HIGH_CONTRADICTION = "HIGH_CONTRADICTION"
    AMBIGUOUS_SUPPRESSION = "AMBIGUOUS_SUPPRESSION"
    MANUAL_AUDIT = "MANUAL_AUDIT"


class EditorialReview(Base, CreatedAtMixin):
    """Immutable log of a human editorial decision."""
    
    __tablename__ = "editorial_reviews"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("narrative_clusters.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Context
    trigger_reason: Mapped[ReviewTriggerReason] = mapped_column(
        Enum(ReviewTriggerReason), nullable=False
    )
    
    # Identity & Action
    reviewer_id: Mapped[str] = mapped_column(String, nullable=False) # e.g. "admin:123"
    action: Mapped[EditorialAction] = mapped_column(Enum(EditorialAction), nullable=False)
    
    notes: Mapped[str] = mapped_column(Text, nullable=True) # Essential for auditability
    
