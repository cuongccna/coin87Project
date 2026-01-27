"""Schemas for raw ingestion endpoints.

These schemas define the API contract for raw data ingestion.
No processing or scoring - raw data only.

Coin87 Philosophy:
- Does NOT predict price
- Does NOT generate trading signals
- Evaluates INFORMATION RELIABILITY over time
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


SourceTypeEnum = Literal["telegram", "twitter", "reddit", "rss"]
IngestResultEnum = Literal[
    "inserted",
    "duplicate_hash",
    "duplicate_url",
    "duplicate_external_ref",
    "validation_error"
]


class RawIngestRequest(BaseModel):
    """Request payload for raw ingestion endpoint."""
    
    source_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique identifier for the source (e.g., 'channel_123', 'user_456')"
    )
    source_type: SourceTypeEnum = Field(
        ...,
        description="Type of source: telegram, twitter, reddit, or rss"
    )
    text_content: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Raw text content from the source"
    )
    url: Optional[str] = Field(
        None,
        max_length=2048,
        description="Canonical URL if available"
    )
    published_at: datetime = Field(
        ...,
        description="Original publish timestamp (must be UTC)"
    )
    external_ref: Optional[str] = Field(
        None,
        max_length=255,
        description="Platform-native identifier (tweet ID, post ID, etc.)"
    )
    raw_metadata: Optional[dict[str, Any]] = Field(
        None,
        description="Additional raw metadata from source"
    )
    
    @field_validator("published_at")
    @classmethod
    def validate_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("published_at must be timezone-aware (UTC)")
        return v


class RawIngestResponse(BaseModel):
    """Response for a single raw ingestion attempt."""
    
    result: IngestResultEnum = Field(
        ...,
        description="Result of the ingestion attempt"
    )
    event_id: Optional[str] = Field(
        None,
        description="UUID of the inserted event (only if result is 'inserted')"
    )
    content_hash: Optional[str] = Field(
        None,
        description="SHA-256 content hash (hex)"
    )
    message: Optional[str] = Field(
        None,
        description="Human-readable result message"
    )


class RawIngestBatchRequest(BaseModel):
    """Request payload for batch raw ingestion."""
    
    items: list[RawIngestRequest] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of items to ingest (max 100 per batch)"
    )
    stop_on_error: bool = Field(
        False,
        description="If true, stop processing on first validation error"
    )


class RawIngestBatchResponse(BaseModel):
    """Response for batch raw ingestion."""
    
    total: int = Field(..., description="Total items in request")
    inserted: int = Field(..., description="Number of items inserted")
    duplicates: int = Field(..., description="Number of duplicate items skipped")
    errors: int = Field(..., description="Number of validation errors")
    results: list[RawIngestResponse] = Field(
        ...,
        description="Individual results for each item"
    )
