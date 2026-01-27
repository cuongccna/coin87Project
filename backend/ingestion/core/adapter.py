from __future__ import annotations

"""BaseAdapter contract for Job A.

Non-negotiable rules:
- Adapter MUST swallow its own exceptions.
- Adapter MUST return partial success if possible.
- Adapter MUST NOT propagate crashes.
- Adapter MUST NOT update existing rows.
- Adapter MUST ONLY insert into information_events (append-only).
"""

import abc
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Protocol

from sqlalchemy.orm import Session

from ingestion.core.fetch_context import FetchContext, SourceConfig


@dataclass(frozen=True, slots=True)
class RawItem:
    """Adapter-specific raw unit, safe to keep in-memory for normalization."""

    source_key: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class NormalizedEvent:
    """Normalized event for insertion into information_events (raw input layer).

    Required schema (as specified by Job A mission):
    - source_id: string
    - source_type: enum/text
    - source_name: string
    - event_time: datetime (UTC)
    - abstract: neutral summary
    - raw_metadata: JSON (dict)
    - content_hash_sha256: string (hex)

    Note: coin87 DB `information_events` stores bytes hash; insertion converts hex->bytes.
    """

    source_id: str
    source_type: str
    source_name: str
    event_time: datetime
    abstract: str
    raw_metadata: dict[str, Any]
    content_hash_sha256: str


class BaseAdapter(abc.ABC):
    """Abstract adapter for Job A."""

    adapter_type: str  # e.g. "rss" | "github" | "telegram" | "reddit"

    @abc.abstractmethod
    def fetch(self, context: FetchContext, source: SourceConfig) -> list[RawItem]:
        """Fetch raw items for a single source.

        MUST swallow exceptions and return [] on failure.
        """

    @abc.abstractmethod
    def normalize(self, raw_item: RawItem, source: SourceConfig) -> Optional[NormalizedEvent]:
        """Normalize a raw item into a NormalizedEvent.

        MUST swallow exceptions and return None if cannot normalize.
        """

    @abc.abstractmethod
    def validate(self, event: NormalizedEvent) -> bool:
        """Validate normalized event prior to insert.

        MUST swallow exceptions and return False on failure.
        """

    @abc.abstractmethod
    def insert(self, event: NormalizedEvent, db_session: Session) -> bool:
        """Insert event into information_events (append-only).

        Returns True if inserted, False if deduplicated or skipped.
        MUST swallow exceptions.
        """

