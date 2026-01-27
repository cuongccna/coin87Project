"""Raw ingestion module for Coin87.

This module handles the insertion of raw information events into the database.
It is the ONLY entry point for new data into the system.

Core principles:
- Store raw data ONLY, no processing or scoring
- Generate content hash for deduplication
- Append-only: never update existing records
- All timestamps must be UTC

Coin87 Philosophy:
- Does NOT predict price
- Does NOT generate trading signals
- Evaluates INFORMATION RELIABILITY over time
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.information_event import InformationEvent


UTC = timezone.utc


class SourceType(str, Enum):
    """Supported source types for raw ingestion."""
    TELEGRAM = "telegram"
    TWITTER = "twitter"
    REDDIT = "reddit"
    RSS = "rss"


class IngestResult(str, Enum):
    """Result of an ingestion attempt."""
    INSERTED = "inserted"
    DUPLICATE_HASH = "duplicate_hash"
    DUPLICATE_URL = "duplicate_url"
    DUPLICATE_EXTERNAL_REF = "duplicate_external_ref"
    VALIDATION_ERROR = "validation_error"


@dataclass(frozen=True, slots=True)
class RawIngestInput:
    """Input payload for raw ingestion.
    
    All fields are raw data from the source with no processing.
    """
    source_id: str                    # Unique identifier for the source (e.g., "telegram_channel_123")
    source_type: SourceType           # Type of source (telegram, twitter, reddit, rss)
    text_content: str                 # Raw text content from the source
    url: Optional[str]                # Canonical URL if available
    published_at: datetime            # Original publish timestamp (must be UTC)
    external_ref: Optional[str] = None  # Platform-native identifier (tweet ID, post ID, etc.)
    raw_metadata: Optional[dict[str, Any]] = None  # Additional raw metadata from source


@dataclass(frozen=True, slots=True)
class RawIngestOutput:
    """Result of a raw ingestion attempt."""
    result: IngestResult
    event_id: Optional[uuid.UUID] = None
    content_hash: Optional[str] = None
    message: Optional[str] = None


def compute_content_hash(*, text_content: str, source_id: str) -> bytes:
    """Compute deterministic SHA-256 hash for deduplication.
    
    Hash is computed from normalized text content + source identifier.
    This allows the same content from different sources to be tracked separately.
    
    Returns:
        32-byte SHA-256 digest
    """
    # Normalize: strip whitespace, lowercase, concatenate with source
    normalized = (text_content or "").strip().lower()
    combined = f"{normalized}\n{source_id.strip()}"
    return hashlib.sha256(combined.encode("utf-8")).digest()


def _validate_input(input_data: RawIngestInput) -> Optional[str]:
    """Validate raw input data.
    
    Returns error message if invalid, None if valid.
    """
    if not input_data.source_id or not input_data.source_id.strip():
        return "source_id is required"
    
    if not input_data.text_content or not input_data.text_content.strip():
        return "text_content is required"
    
    if input_data.published_at.tzinfo is None:
        return "published_at must be timezone-aware (UTC)"
    
    if input_data.published_at.utcoffset() != timedelta(0):
        return "published_at must be UTC"
    
    # Reject future timestamps (with 5 minute tolerance for clock skew)
    max_allowed = datetime.now(UTC) + timedelta(minutes=5)
    if input_data.published_at > max_allowed:
        return "published_at cannot be in the future"
    
    return None


def _extract_title(text_content: str, max_length: int = 200) -> str:
    """Extract a title from text content.
    
    Uses first line or first N characters as title.
    """
    # Take first line
    first_line = text_content.strip().split("\n")[0].strip()
    
    if len(first_line) <= max_length:
        return first_line
    
    # Truncate at word boundary
    truncated = first_line[:max_length].rsplit(" ", 1)[0]
    return truncated + "..." if truncated else first_line[:max_length] + "..."


def _extract_excerpt(text_content: str, max_length: int = 500) -> Optional[str]:
    """Extract body excerpt from text content.
    
    Returns None if content is short enough to be title-only.
    """
    stripped = text_content.strip()
    lines = stripped.split("\n")
    
    # If only one short line, no excerpt needed
    if len(lines) == 1 and len(stripped) <= 200:
        return None
    
    # Skip first line (used as title), take rest as excerpt
    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else stripped
    
    if not body:
        return None
    
    if len(body) <= max_length:
        return body
    
    return body[:max_length].rsplit(" ", 1)[0] + "..."


def check_duplicate_by_hash(db: Session, content_hash: bytes) -> bool:
    """Check if content hash already exists in database."""
    stmt = select(InformationEvent.id).where(
        InformationEvent.content_hash_sha256 == content_hash
    ).limit(1)
    result = db.execute(stmt).scalar_one_or_none()
    return result is not None


def check_duplicate_by_url(db: Session, source_ref: str, url: str) -> bool:
    """Check if URL already exists for this source."""
    stmt = select(InformationEvent.id).where(
        InformationEvent.source_ref == source_ref,
        InformationEvent.canonical_url == url
    ).limit(1)
    result = db.execute(stmt).scalar_one_or_none()
    return result is not None


def check_duplicate_by_external_ref(db: Session, source_ref: str, external_ref: str) -> bool:
    """Check if external reference already exists for this source."""
    stmt = select(InformationEvent.id).where(
        InformationEvent.source_ref == source_ref,
        InformationEvent.external_ref == external_ref
    ).limit(1)
    result = db.execute(stmt).scalar_one_or_none()
    return result is not None


def ingest_raw(db: Session, input_data: RawIngestInput) -> RawIngestOutput:
    """Ingest a single raw information event.
    
    This is the primary entry point for raw data ingestion.
    
    Deduplication strategy (checked in order):
    1. Content hash - exact content match for this source
    2. External reference - platform-native ID (if provided)
    3. Canonical URL - same URL for this source (if provided)
    
    Args:
        db: SQLAlchemy session
        input_data: Raw input payload
        
    Returns:
        RawIngestOutput with result status and event ID if inserted
    """
    # Validate input
    validation_error = _validate_input(input_data)
    if validation_error:
        return RawIngestOutput(
            result=IngestResult.VALIDATION_ERROR,
            message=validation_error
        )
    
    # Compute content hash
    content_hash = compute_content_hash(
        text_content=input_data.text_content,
        source_id=input_data.source_id
    )
    content_hash_hex = content_hash.hex()
    
    # Build source reference (combines source_type and source_id)
    source_ref = f"{input_data.source_type.value}:{input_data.source_id}"
    
    # Check duplicates in order of specificity
    if check_duplicate_by_hash(db, content_hash):
        return RawIngestOutput(
            result=IngestResult.DUPLICATE_HASH,
            content_hash=content_hash_hex,
            message="Content hash already exists"
        )
    
    if input_data.external_ref and check_duplicate_by_external_ref(
        db, source_ref, input_data.external_ref
    ):
        return RawIngestOutput(
            result=IngestResult.DUPLICATE_EXTERNAL_REF,
            content_hash=content_hash_hex,
            message=f"External reference {input_data.external_ref} already exists"
        )
    
    if input_data.url and check_duplicate_by_url(db, source_ref, input_data.url):
        return RawIngestOutput(
            result=IngestResult.DUPLICATE_URL,
            content_hash=content_hash_hex,
            message=f"URL already exists for this source"
        )
    
    # Prepare event data
    now = datetime.now(UTC)
    event_id = uuid.uuid4()
    
    # Build raw payload (preserve all original data)
    raw_payload = {
        "source_type": input_data.source_type.value,
        "source_id": input_data.source_id,
        "text_content": input_data.text_content,
        "url": input_data.url,
        "external_ref": input_data.external_ref,
        "published_at_iso": input_data.published_at.isoformat(),
        **(input_data.raw_metadata or {})
    }
    
    # Create event
    event = InformationEvent(
        id=event_id,
        source_ref=source_ref,
        external_ref=input_data.external_ref,
        canonical_url=input_data.url,
        title=_extract_title(input_data.text_content),
        body_excerpt=_extract_excerpt(input_data.text_content),
        raw_payload=raw_payload,
        content_hash_sha256=content_hash,
        event_time=input_data.published_at,
        observed_at=now,
    )
    
    db.add(event)
    db.flush()  # Flush to catch any DB-level constraint violations
    
    return RawIngestOutput(
        result=IngestResult.INSERTED,
        event_id=event_id,
        content_hash=content_hash_hex,
        message="Event inserted successfully"
    )


def ingest_raw_batch(
    db: Session,
    inputs: list[RawIngestInput],
    *,
    stop_on_error: bool = False
) -> list[RawIngestOutput]:
    """Ingest multiple raw information events.
    
    Args:
        db: SQLAlchemy session
        inputs: List of raw input payloads
        stop_on_error: If True, stop processing on first validation error
        
    Returns:
        List of RawIngestOutput, one per input (in same order)
    """
    results: list[RawIngestOutput] = []
    
    for input_data in inputs:
        try:
            output = ingest_raw(db, input_data)
            results.append(output)
            
            if stop_on_error and output.result == IngestResult.VALIDATION_ERROR:
                break
                
        except Exception as e:
            # Never propagate exceptions - return error result instead
            results.append(RawIngestOutput(
                result=IngestResult.VALIDATION_ERROR,
                message=f"Unexpected error: {type(e).__name__}: {str(e)}"
            ))
            
            if stop_on_error:
                break
    
    return results
