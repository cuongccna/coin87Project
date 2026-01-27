from __future__ import annotations

"""Reddit adapter (SKELETON ONLY).

Explicitly not implemented in this phase.
This file exists to lock the adapter contract and source registry wiring.
"""

from sqlalchemy.orm import Session

from ingestion.core.adapter import BaseAdapter, NormalizedEvent, RawItem
from ingestion.core.fetch_context import FetchContext, SourceConfig


class RedditAdapter(BaseAdapter):
    adapter_type = "reddit"

    def fetch(self, context: FetchContext, source: SourceConfig) -> list[RawItem]:
        # Skeleton: no implementation.
        return []

    def normalize(self, raw_item: RawItem, source: SourceConfig) -> NormalizedEvent | None:
        return None

    def validate(self, event: NormalizedEvent) -> bool:
        return False

    def insert(self, event: NormalizedEvent, db_session: Session) -> bool:
        return False

