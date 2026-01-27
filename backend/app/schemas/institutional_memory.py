"""Schemas for institutional memory endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.decision_environment import DecisionEnvironmentResponse


class DecisionContextResponse(BaseModel):
    context_id: str
    context_type: str
    context_time: datetime
    description: Optional[str] = None


class DecisionImpactRecordResponse(BaseModel):
    recorded_at: datetime
    environment_snapshot_id: Optional[str] = None
    qualitative_outcome: str
    learning_flags: list[str] = Field(default_factory=list)


class DecisionHistoryItemResponse(BaseModel):
    context: DecisionContextResponse
    decision_environment_at_time: Optional[DecisionEnvironmentResponse] = None
    impacts: list[DecisionImpactRecordResponse] = Field(default_factory=list)

