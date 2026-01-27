"""SQLAlchemy declarative base and shared mixins.

Institutional rationale:
- UUID primary keys to avoid information leakage (no sequential IDs) and to support
  cross-system audit references.
- Explicit UTC-only, timezone-aware timestamps for strict audit timelines.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class UUIDPrimaryKeyMixin:
    """UUID primary key mixin (application-generated)."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class CreatedAtMixin:
    """Created-at timestamp mixin (UTC timestamptz).

    Note: Postgres `timestamptz` is stored normalized; clients must supply UTC
    for semantic correctness. Model-level validators should enforce UTC where
    appropriate for non-server-generated timestamps.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class UpdatedAtMixin:
    """Updated-at timestamp mixin (UTC timestamptz).

    Only use for mutable tables. Many coin87 entities are immutable/append-only.
    """

    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
    )

