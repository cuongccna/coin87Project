"""InformationEvent model.

Institutional rationale:
InformationEvents are immutable raw inputs that enter the decision environment.
They are not "news" objects and must never be rewritten, because governance and
post-mortems require an audit trail of what was available and when.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    LargeBinary,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.core.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


UTC = timezone.utc


@dataclass(frozen=True, slots=True)
class InformationEventNaturalKey:
    """Natural key components used for deduplication decisions."""

    source_ref: str
    external_ref: Optional[str]
    canonical_url: Optional[str]


class InformationEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Immutable raw input event.

    This table intentionally stores:
    - attribution (source_ref)
    - immutable observed timestamps (observed_at, event_time when provided)
    - a bounded excerpt (body_excerpt) and raw payload for audit/reprocessing

    It intentionally does NOT store:
    - any trading view, sentiment-only fields, or derived "scores"
    """

    __tablename__ = "information_events"

    # Attribution and identifiers
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    external_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    canonical_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Minimal content fields (never full scraped article text)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Raw payload from ingestion (RSS item, platform JSON, etc.)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Deterministic content hash for fuzzy/semantic dedupe layering.
    # Stored as 32-byte sha256 digest.
    content_hash_sha256: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)

    # Temporal fields
    event_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "octet_length(content_hash_sha256) = 32",
            name="ck_information_events_sha256_len",
        ),
        Index(
            "ix_information_events_observed_at",
            "observed_at",
        ),
        Index(
            "ix_information_events_source_ref_observed_at",
            "source_ref",
            "observed_at",
        ),
        # Partial unique indexes for platform-native identifiers.
        Index(
            "ux_information_events_source_ref_external_ref",
            "source_ref",
            "external_ref",
            unique=True,
            postgresql_where=text("external_ref IS NOT NULL"),
        ),
        Index(
            "ux_information_events_source_ref_canonical_url",
            "source_ref",
            "canonical_url",
            unique=True,
            postgresql_where=text("canonical_url IS NOT NULL"),
        ),
    )

    @validates("observed_at", "event_time")
    def _validate_utc(self, key: str, value: Optional[datetime]) -> Optional[datetime]:
        """Enforce timezone-aware UTC datetimes for audit correctness."""
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{key} must be timezone-aware (UTC).")
        if value.utcoffset() != timedelta(0):
            raise ValueError(f"{key} must be UTC (offset 0).")
        return value.astimezone(UTC)

    def natural_key(self) -> InformationEventNaturalKey:
        return InformationEventNaturalKey(
            source_ref=self.source_ref,
            external_ref=self.external_ref,
            canonical_url=self.canonical_url,
        )

