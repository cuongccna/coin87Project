"""AI Enrichment Worker - Process InformationEvents để tạo enriched analysis.

Chạy độc lập, process các events đã được scored cao.
Không mock - tất cả dùng API thực.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# Add backend to path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.core.env import load_env_if_present
from app.core.database import get_session
from app.models.information_event import InformationEvent
from app.models.information_event_enrichment import InformationEventEnrichment
from ingestion.core.ai_summarizer import get_summarizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("coin87.jobs.ai_enrichment")


def process_unenriched_events(
    session: Session,
    batch_size: int = 10,
    lookback_hours: int = 24,
    min_content_length: int = 200,
) -> int:
    """
    Process InformationEvents chưa có enrichment.
    
    Args:
        session: DB session
        batch_size: Số events process mỗi lần
        lookback_hours: Chỉ process events trong N giờ gần nhất
        min_content_length: Chỉ process events có content_text >= N chars
        
    Returns:
        Số events đã process
    """
    summarizer = get_summarizer()
    
    # Find unenriched events with detailed content
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    
    stmt = (
        select(InformationEvent)
        .outerjoin(
            InformationEventEnrichment,
            InformationEvent.id == InformationEventEnrichment.information_event_id
        )
        .where(
            and_(
                InformationEventEnrichment.id.is_(None),  # Chưa có enrichment
                InformationEvent.observed_at >= cutoff_time,
                InformationEvent.content_text.isnot(None),
                # SQLAlchemy length check
            )
        )
        .order_by(InformationEvent.observed_at.desc())
        .limit(batch_size)
    )
    
    events = session.execute(stmt).scalars().all()
    
    if not events:
        logger.info("No unenriched events found")
        return 0
    
    logger.info(f"Found {len(events)} events to enrich")
    
    processed = 0
    for event in events:
        # Skip if content quá ngắn (check runtime vì SQL không hỗ trợ length trong WHERE portable)
        if not event.content_text or len(event.content_text) < min_content_length:
            logger.debug(f"Skipping event {event.id}: content too short")
            continue
        
        try:
            logger.info(f"Enriching event {event.id}: {event.title[:60]}...")
            
            # Call AI summarizer
            analysis = summarizer.analyze(
                title=event.title,
                content_text=event.content_text,
                url=event.canonical_url,
                source_name=event.source_ref,
            )
            
            # Create enrichment record
            enrichment = InformationEventEnrichment(
                information_event_id=event.id,
                ai_summary=analysis.summary,
                entities=analysis.entities,
                sentiment=analysis.sentiment,
                confidence=analysis.confidence,
                keywords=analysis.keywords,
                category=analysis.category,
                # worth_click_score sẽ được set bởi RSS adapter
                # filter_decision sẽ được set bởi RSS adapter
            )
            
            session.add(enrichment)
            session.commit()
            
            logger.info(
                f"✓ Enriched event {event.id}: "
                f"sentiment={analysis.sentiment}, "
                f"confidence={analysis.confidence:.2f}, "
                f"category={analysis.category}"
            )
            processed += 1
            
        except Exception as e:
            logger.exception(f"Failed to enrich event {event.id}: {e}")
            session.rollback()
            continue
    
    return processed


def main():
    parser = argparse.ArgumentParser(description="AI Enrichment Worker")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of events to process per run (default: 10)"
    )
    parser.add_argument(
        "--lookback-hours",
        type=int,
        default=24,
        help="Only process events from last N hours (default: 24)"
    )
    parser.add_argument(
        "--min-content-length",
        type=int,
        default=200,
        help="Minimum content_text length to process (default: 200)"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuously with interval (not implemented yet)"
    )
    
    args = parser.parse_args()
    
    load_env_if_present()
    
    logger.info("=" * 60)
    logger.info("AI Enrichment Worker Started")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Lookback hours: {args.lookback_hours}")
    logger.info(f"Min content length: {args.min_content_length}")
    logger.info("=" * 60)
    
    try:
        with get_session() as session:
            processed = process_unenriched_events(
                session=session,
                batch_size=args.batch_size,
                lookback_hours=args.lookback_hours,
                min_content_length=args.min_content_length,
            )
            
            logger.info("=" * 60)
            logger.info(f"AI Enrichment Complete: {processed} events processed")
            logger.info("=" * 60)
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
