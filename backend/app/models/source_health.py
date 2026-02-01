from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base

class SourceHealth(Base):
    """Tracks operational health and rate limit state for ingestion sources.
    
    This state allows the circuit breaker and smart rate controller to persist
    decisions across process boundaries (e.g. between cron runs).
    """
    __tablename__ = "source_health_states"

    source_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    
    # Circuit Breaker State
    status: Mapped[str] = mapped_column(String, default="HEALTHY")  # HEALTHY, DEGRADED, OPEN
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    next_allowed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Conditional Fetch State
    etag: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_modified: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Operational Metrics
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Identity / Fingerprint (Optional sticky session)
    cookie_jar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON serialized cookies if needed
