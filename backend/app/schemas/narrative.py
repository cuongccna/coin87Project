"""Schemas for narrative contamination endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


NarrativeStatus = Literal["ACTIVE", "FADING", "DORMANT"]
RecommendedPosture = Literal["IGNORE", "REVIEW", "DELAY"]


class NarrativeRiskResponse(BaseModel):
    risk_type: str
    severity: int = Field(ge=1, le=5)
    recommended_posture: RecommendedPosture
    valid_from: datetime
    valid_to: Optional[datetime] = None
    occurrence_count: int = 1


class NarrativeResponse(BaseModel):
    narrative_id: str
    theme: str
    saturation_level: int = Field(ge=1, le=5)
    status: NarrativeStatus
    first_seen_at: datetime
    last_seen_at: datetime


class NarrativeDetailResponse(NarrativeResponse):
    linked_risks: list[NarrativeRiskResponse] = Field(default_factory=list)

