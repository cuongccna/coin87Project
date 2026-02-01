"""Repository for InversionFeed operations."""
from datetime import datetime
from typing import List, Optional, Tuple, Any
from uuid import UUID

from sqlalchemy import desc, func, select, case
from sqlalchemy.orm import Session

from app.models.inversion_feed import InversionFeed
from app.schemas.inversion_feed import InversionFeedCreate


def create_inversion_feed(db: Session, data: InversionFeedCreate) -> InversionFeed:
    """Create a new inversion feed record."""
    # Map pydantic fields to model fields
    # Note: schema.metadata maps to model.metadata_
    db_obj = InversionFeed(
        symbol=data.symbol,
        feed_type=data.feed_type,
        direction=data.direction,
        value=data.value,
        confidence=data.confidence,
        payload=data.payload,
        metadata_=data.metadata,
        external_id=data.external_id,
        source_id=data.source_id,
        status="new",
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_inversion_feed(db: Session, feed_id: UUID) -> Optional[InversionFeed]:
    """Get a single feed by ID."""
    return db.get(InversionFeed, feed_id)


def list_inversion_feeds(
    db: Session,
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    narrative_risk: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[InversionFeed], int]:
    """List feeds with filtering."""
    stmt = select(InversionFeed)
    count_stmt = select(func.count()).select_from(InversionFeed)

    if symbol:
        stmt = stmt.where(InversionFeed.symbol == symbol)
        count_stmt = count_stmt.where(InversionFeed.symbol == symbol)
    if status:
        stmt = stmt.where(InversionFeed.status == status)
        count_stmt = count_stmt.where(InversionFeed.status == status)
    if start:
        stmt = stmt.where(InversionFeed.created_at >= start)
        count_stmt = count_stmt.where(InversionFeed.created_at >= start)
    if end:
        stmt = stmt.where(InversionFeed.created_at <= end)
        count_stmt = count_stmt.where(InversionFeed.created_at <= end)
    if narrative_risk:
        # Filter by narrative_risk stored inside JSON payload (case-insensitive)
        risk_value = InversionFeed.payload['narrative_risk'].astext
        stmt = stmt.where(func.lower(risk_value) == narrative_risk.lower())
        count_stmt = count_stmt.where(func.lower(risk_value) == narrative_risk.lower())

    # Order by narrative_risk (High > Medium > Low) then created_at desc
    # Order by narrative_risk (High > Medium > Low) then created_at desc
    risk_value = InversionFeed.payload['narrative_risk'].astext
    stmt = stmt.order_by(
        case(
            (func.lower(risk_value) == 'high', 3),
            (func.lower(risk_value) == 'medium', 2),
            (func.lower(risk_value) == 'low', 1),
            else_=0
        ).desc(),
        desc(InversionFeed.created_at)
    )
    stmt = stmt.limit(limit).offset(offset)

    total = db.scalar(count_stmt) or 0
    items = db.scalars(stmt).all()
    
    return list(items), total


def update_inversion_status(
    db: Session, feed_id: UUID, status: str, processed_at: Optional[datetime] = None
) -> Optional[InversionFeed]:
    """Update status of a feed."""
    feed = db.get(InversionFeed, feed_id)
    if feed:
        feed.status = status
        if processed_at:
            feed.processed_at = processed_at
        db.add(feed)
        db.commit()
        db.refresh(feed)
    return feed
