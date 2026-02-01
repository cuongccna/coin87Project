"""Inversion Feed API endpoints."""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.repositories import inversion_repo
from app.schemas.inversion_feed import (
    InversionFeedCreate,
    InversionFeedListResponse,
    InversionFeedRead,
)
from app.services import inversion_service

router = APIRouter()


@router.post(
    "/",
    response_model=InversionFeedRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Inversion Feed",
)
def create_inversion_feed(
    data: InversionFeedCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
):
    """
    Create a new inversion feed and schedule background processing.
    """
    return inversion_service.create_inversion_feed_and_enqueue(db, data, background_tasks)


@router.get(
    "/",
    response_model=InversionFeedListResponse,
    summary="List Inversion Feeds",
)
def list_inversion_feeds(
    symbol: str = Query(None, description="Filter by symbol"),
    status: str = Query(None, description="Filter by status"),
    narrative_risk: str = Query(None, description="Filter by narrative risk (HIGH|MEDIUM|LOW)"),
    start: datetime = Query(None, description="Start date (ISO)"),
    end: datetime = Query(None, description="End date (ISO)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session),
):
    """
    List inversion feeds with filtering.
    """
    items, total = inversion_repo.list_inversion_feeds(
        db, symbol=symbol, status=status, narrative_risk=narrative_risk, start=start, end=end, limit=limit, offset=offset
    )
    return {"total": total, "items": items}


@router.get(
    "/{feed_id}",
    response_model=InversionFeedRead,
    summary="Get Inversion Feed",
)
def get_inversion_feed(
    feed_id: UUID,
    db: Session = Depends(get_db_session),
):
    """
    Get a single inversion feed by ID.
    """
    feed = inversion_repo.get_inversion_feed(db, feed_id)
    if not feed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found")
    return feed
