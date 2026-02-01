"""Service logic for Inversion Feeds."""
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.repositories import inversion_repo
from app.schemas.inversion_feed import InversionFeedCreate
from app.services.redis_client import get_redis
import json

logger = logging.getLogger(__name__)


def create_inversion_feed_and_enqueue(
    db: Session, 
    data: InversionFeedCreate, 
    background_tasks: BackgroundTasks
):
    """Create feed and schedule background processing."""
    feed = inversion_repo.create_inversion_feed(db, data)
    # Publish lightweight notification to Redis channel for real-time UI updates
    try:
        r = get_redis()
        if r is not None:
            payload = {
                "id": str(feed.id),
                "symbol": feed.symbol,
                "feed_type": feed.feed_type,
                "direction": feed.direction,
                "confidence": feed.confidence,
                "created_at": feed.created_at.isoformat(),
            }
            # publish as JSON string
            try:
                r.publish("inversion:updates", json.dumps(payload))
            except Exception:
                # best-effort: do not fail creation if publish fails
                pass
    except Exception:
        pass
    
    # Schedule the task wrapper which manages its own session
    # Note: BackgroundTasks runs after the response is sent.
    background_tasks.add_task(process_inversion_feed_task, feed.id)
    
    return feed


def process_inversion_feed_task(feed_id: UUID):
    """Background task wrapper creating its own DB session."""
    try:
        # Use context manager to ensure session closure
        with SessionLocal() as db:
            process_inversion_feed(db, feed_id)
    except Exception as e:
        logger.error(f"Error processing inversion feed {feed_id}: {e}")


def process_inversion_feed(db: Session, feed_id: UUID):
    """Core processing logic (idempotent)."""
    feed = inversion_repo.get_inversion_feed(db, feed_id)
    if not feed:
        logger.warning(f"Inversion feed {feed_id} not found during processing")
        return
    
    if feed.status == "processed":
        logger.info(f"Inversion feed {feed_id} already processed")
        return

    # --- Enrichment Logic (Stub) ---
    # 1. Normalize confidence (clamp 0..1) if present
    if feed.confidence is not None:
        # We can't easily modify the object and expect SQLAlchemy to pick it up unless we attach it to session 
        # But 'feed' is attached to 'db'. The repo.update... pulls it again or updates it.
        # Let's perform logic then call update.
        pass

    # 2. Simple example derived logic: 
    # If using 'value', assume it might need stored in metadata as 'original_value' if we normalized it.
    # For now, just mark processed.

    # Update status
    inversion_repo.update_inversion_status(
        db, 
        feed_id, 
        status="processed", 
        processed_at=datetime.now(timezone.utc)
    )
    logger.info(f"Successfully processed inversion feed {feed_id}")
