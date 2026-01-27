"""Schemas for decision risk endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


RecommendedPosture = Literal["IGNORE", "REVIEW", "DELAY"]


class TimeRelevance(BaseModel):
    valid_from: datetime
    valid_to: Optional[datetime] = None


class DecisionRiskEventResponse(BaseModel):
    """Abstracted risk event suitable for IC materials (no raw inputs)."""

    risk_type: str
    severity: int = Field(ge=1, le=5)
    affected_decisions: list[str]
    recommended_posture: RecommendedPosture
    detected_at: datetime
    time_relevance: TimeRelevance

