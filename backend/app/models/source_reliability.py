"""SourceReliability model.

Persists the computed trust index for each source.
Derived from historical participation in reliable vs noisy clusters.

Coin87 Philosophy:
- Source behavior analysis
- No manual blacklisting (algorithmic trust)
- Range 0.1 - 1.0 (never 0)
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, UpdatedAtMixin


UTC = timezone.utc


class SourceReliability(UpdatedAtMixin, Base):
    """Derived reliability metrics for a specific source."""
    
    __tablename__ = "source_reliability"
    
    # source_ref is the natural key from InformationEvent (e.g. "twitter:user123")
    source_ref: Mapped[str] = mapped_column(String, primary_key=True)
    
    trust_index: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    
    # Evidence / Metrics
    total_mentions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confirmed_mentions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    noise_mentions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    average_lifespan_minutes: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Phase 5: Evolution Metrics (Rolling Window)
    rolling_confirmed_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rolling_noise_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    persistence_alignment: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    
    last_computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  
        server_default=func.now(),
        onupdate=func.now()
    )
