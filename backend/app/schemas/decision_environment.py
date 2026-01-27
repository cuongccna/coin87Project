"""Schemas for decision environment endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


EnvironmentState = Literal["CLEAN", "CAUTION", "CONTAMINATED"]


class DecisionEnvironmentResponse(BaseModel):
    """Decision environment summary (low-noise, deterministic)."""

    environment_state: EnvironmentState
    dominant_risks: list[str] = Field(default_factory=list)
    risk_density: int
    snapshot_time: datetime
    guidance: str
    data_stale: bool = False
    staleness_seconds: int | None = None

