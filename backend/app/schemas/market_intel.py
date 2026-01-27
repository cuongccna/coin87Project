"""Schemas for information reliability dashboard (read-only).

This is a UI-facing summary object:
- information-reliability-first
- minimal text
- backend-driven scoring (frontend must not compute)

Coin87 Core Philosophy:
- Does NOT predict price
- Does NOT generate trading signals
- Evaluates INFORMATION RELIABILITY over time
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


ReliabilityLevel = Literal["high", "medium", "low", "unverified"]
InformationCategory = Literal["narrative", "event", "correction", "rumor"]


class InformationReliabilityState(BaseModel):
    """Current state of information environment reliability."""
    overall_reliability: ReliabilityLevel
    confirmation_rate: int = Field(ge=0, le=100, description="% of information confirmed by multiple sources")
    contradiction_rate: int = Field(ge=0, le=100, description="% of information that has been contradicted")
    active_narratives_count: int = Field(ge=0, description="Number of active narrative clusters")


class InformationSignal(BaseModel):
    """A discrete piece of information evaluated for reliability."""
    title: str
    reliability_score: float = Field(ge=0, le=10, description="Reliability score based on source behavior")
    reliability_level: ReliabilityLevel
    confirmation_count: int = Field(ge=0, description="Number of sources confirming this information")
    persistence_hours: int = Field(ge=0, description="How long this information has persisted")
    category: InformationCategory
    narrative_id: Optional[str] = Field(None, description="Linked narrative cluster ID if applicable")


class InformationReliabilityResponse(BaseModel):
    """Response object for information reliability dashboard."""
    state: InformationReliabilityState
    signals: list[InformationSignal]

