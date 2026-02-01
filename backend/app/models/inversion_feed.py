"""InversionFeed model.

Represents an incoming signal/feed for inversion analysis.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class InversionFeed(Base):
    __tablename__ = "inversion_feeds"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    external_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    feed_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 'price-inversion', etc.
    direction: Mapped[str] = mapped_column(String(16), nullable=False)  # 'up', 'down', 'neutral'
    
    value: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="new")
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now(), 
        default=lambda: datetime.now(timezone.utc)
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_inversion_feeds_created_at", "created_at"),
        Index("ix_inversion_feeds_symbol", "symbol"),
        Index("ix_inversion_feeds_status", "status"),
        Index("ix_inversion_feeds_external_id", "external_id", unique=True, postgresql_where=(external_id.is_not(None))),
        Index("gin_inversion_feeds_payload", "payload", postgresql_using="gin"),
        Index("gin_inversion_feeds_metadata", "metadata", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<InversionFeed(id={self.id}, symbol={self.symbol}, status={self.status})>"
