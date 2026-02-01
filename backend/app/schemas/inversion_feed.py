"""Pydantic schemas for InversionFeed."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InversionFeedBase(BaseModel):
    symbol: str = Field(..., max_length=64, description="Ticker symbol or asset identifier")
    feed_type: str = Field(..., max_length=32, description="Type of inversion signal")
    direction: str = Field(..., max_length=16, description="Direction of signal")
    value: Optional[float] = Field(None, description="Numeric magnitude of signal")
    confidence: Optional[float] = Field(None, description="Confidence score 0.0-1.0")
    payload: Optional[dict] = Field(None, description="Raw payload from source")
    metadata: Optional[dict] = Field(None, alias="metadata_", description="Internal metadata")
    external_id: Optional[str] = Field(None, description="External identifier from source")
    source_id: Optional[UUID] = Field(None, description="Source ID reference")

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        # Extended to include Risk Levels for Narrative Risk Feed
        if v.lower() not in {"up", "down", "neutral", "high", "medium", "low"}:
            raise ValueError("direction must be 'up', 'down', 'neutral', 'high', 'medium', or 'low'")
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v


class InversionFeedCreate(InversionFeedBase):
    pass


class InversionFeedRead(InversionFeedBase):
    id: UUID
    status: str
    created_at: datetime
    processed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class InversionFeedListResponse(BaseModel):
    total: int
    items: List[InversionFeedRead]
