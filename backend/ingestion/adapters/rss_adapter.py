from __future__ import annotations

"""RSS adapter (FULL) for Job A.

Scope:
- Fetch RSS/Atom feeds using FetchContext.
- Normalize into NormalizedEvent.
- Validate minimal fields.
- Insert append-only into information_events with ignore-on-conflict.

Non-goals (explicit):
- No scoring, classification, or risk evaluation.
- No updates to existing rows.
"""

import re
from datetime import datetime, timezone
from typing import Any, Optional

import feedparser
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.information_event import InformationEvent
from app.models.information_event_enrichment import InformationEventEnrichment
from ingestion.core.adapter import BaseAdapter, NormalizedEvent, RawItem
from ingestion.core.dedup import compute_content_hash_sha256_bytes, compute_content_hash_sha256_hex
from ingestion.core.fetch_context import FetchContext, SourceConfig
from ingestion.core.content_fetcher import fetch_and_extract
from ingestion.core.content_filter import get_filter, FilterDecision
from ingestion.core.worth_click_scorer import get_scorer


UTC = timezone.utc


def _strip_html(text: str) -> str:
    # Minimal sanitization; RSS summaries often contain HTML.
    t = re.sub(r"<[^>]+>", " ", text or "")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.utcoffset() is None:
        # Treat naive as UTC to preserve audit ordering (source-provided timestamps can be incomplete).
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _entry_time(entry: Any) -> datetime:
    # feedparser provides .published_parsed / .updated_parsed (time.struct_time)
    now = datetime.now(tz=UTC)
    for key in ("published_parsed", "updated_parsed"):
        st = getattr(entry, key, None)
        if st:
            try:
                return _to_utc(datetime(*st[:6], tzinfo=UTC))
            except Exception:  # noqa: BLE001
                continue
    return now


class RssAdapter(BaseAdapter):
    adapter_type = "rss"

    def fetch(self, context: FetchContext, source: SourceConfig) -> list[RawItem]:
        """Fetch RSS with pre-filter and worth-click scoring."""
        content_filter = get_filter()
        scorer = get_scorer()
        
        try:
            status, body, meta = context.fetch_text(source=source)
            if body is None:
                return []

            feed = feedparser.parse(body)
            items: list[RawItem] = []
            for entry in feed.entries or []:
                title = getattr(entry, "title", None) or ""
                summary = getattr(entry, "summary", None)
                link = getattr(entry, "link", None)
                
                # 1. Pre-filter check
                filter_result = content_filter.check(
                    title=title,
                    summary=summary,
                    categories=getattr(entry, "tags", None),
                    url=link,
                )
                
                # Skip rejected items (unless filter allows pass)
                if filter_result.decision != FilterDecision.PASS:
                    continue
                
                # 2. Worth-click scoring
                entry_time = _entry_time(entry)
                score_breakdown = scorer.score(
                    title=title,
                    summary=summary,
                    source_tier=getattr(source, "tier", 3),
                    source_priority=source.priority,
                    published_time=entry_time,
                    filter_penalty=filter_result.score_penalty,
                    worth_click_keywords=getattr(source, "worth_click_keywords", None),
                )
                
                # Build payload
                payload = {
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "id": getattr(entry, "id", None),
                    "published": getattr(entry, "published", None),
                    "updated": getattr(entry, "updated", None),
                    "published_parsed": getattr(entry, "published_parsed", None),
                    "updated_parsed": getattr(entry, "updated_parsed", None),
                    # Store scoring metadata
                    "_filter_decision": filter_result.decision.value,
                    "_filter_reason": filter_result.reason,
                    "_worth_click_score": score_breakdown.final_score,
                    "_worth_click_breakdown": {
                        "base": score_breakdown.base_score,
                        "tier": score_breakdown.tier_bonus,
                        "priority": score_breakdown.priority_bonus,
                        "keyword": score_breakdown.keyword_bonus,
                        "time": score_breakdown.time_bonus,
                        "penalty": score_breakdown.filter_penalty,
                    },
                }
                
                # 3. Decide detailed fetch strategy
                fetch_strategy = getattr(source, "fetch_strategy", "scored")
                should_fetch = False
                
                if fetch_strategy == "always":
                    should_fetch = True
                elif fetch_strategy == "scored":
                    should_fetch = scorer.should_fetch_detailed(score_breakdown)
                # "never" = should_fetch remains False
                
                # 4. Optionally perform detailed fetch
                if link and should_fetch:
                    try:
                        html, text, meta_fetch = fetch_and_extract(str(link), context, source.key)
                        if html is not None:
                            payload["content_html"] = html
                        if text is not None:
                            payload["content_text"] = text
                        if meta_fetch and meta_fetch.get("excerpt"):
                            payload["content_excerpt"] = meta_fetch.get("excerpt")
                        payload["content_fetch_meta"] = meta_fetch
                    except Exception:
                        # Non-fatal: attach nothing and continue with RSS item
                        pass

                items.append(RawItem(source_key=source.key, payload=payload))
            return items
        except Exception:  # noqa: BLE001
            return []

    def normalize(self, raw_item: RawItem, source: SourceConfig) -> Optional[NormalizedEvent]:
        try:
            p = raw_item.payload
            title = _strip_html(str(p.get("title") or "")).strip()
            summary = _strip_html(str(p.get("summary") or "")).strip()
            link = str(p.get("link") or "").strip() or None
            ext_id = str(p.get("id") or "").strip() or None

            # Neutral abstract: title + summary (no sentiment, no scoring).
            abstract = title
            if summary and summary.lower() not in (title.lower(),):
                abstract = f"{title}. {summary}" if title else summary
            abstract = abstract.strip()
            if len(abstract) > 2000:
                abstract = abstract[:2000].rstrip()

            source_name = source.name or source.key
            # Dedup rule (required): sha256(abstract + source_name)
            h_hex = compute_content_hash_sha256_hex(abstract=abstract, source_name=source_name)

            # raw_metadata carries source identity and RSS fields.
            raw_metadata: dict[str, Any] = {
                "source_key": source.key,
                "source_type": source.type,
                "source_name": source_name,
                "url": source.url,
                "rss": {
                    "title": title or None,
                    "summary": summary or None,
                    "link": link,
                    "external_id": ext_id,
                    "published": p.get("published"),
                    "updated": p.get("updated"),
                },
            }
            # If detailed fetch attached content, surface it in raw_metadata
            if p.get("content_html"):
                raw_metadata["content_html"] = p.get("content_html")
            if p.get("content_text"):
                raw_metadata["content_text"] = p.get("content_text")
            if p.get("content_excerpt"):
                raw_metadata["content_excerpt"] = p.get("content_excerpt")
            if p.get("content_fetch_meta"):
                raw_metadata["content_fetch_meta"] = p.get("content_fetch_meta")

            # event_time: best-effort from feed entry time.
            event_time = _entry_time(type("E", (), p))

            # source_id: stable ID for this item if available; else fallback to hash.
            source_id = ext_id or link or h_hex

            return NormalizedEvent(
                source_id=source_id,
                source_type=source.type,
                source_name=source_name,
                event_time=event_time,
                abstract=abstract,
                raw_metadata=raw_metadata,
                content_hash_sha256=h_hex,
            )
        except Exception:  # noqa: BLE001
            return None

    def validate(self, event: NormalizedEvent) -> bool:
        try:
            if not event.source_id or not event.source_name or not event.source_type:
                return False
            if not event.abstract or len(event.abstract.strip()) < 8:
                return False
            if event.event_time.tzinfo is None or event.event_time.utcoffset() is None:
                return False
            return True
        except Exception:  # noqa: BLE001
            return False

    def insert(self, event: NormalizedEvent, db_session: Session) -> bool:
        try:
            # Map NormalizedEvent -> InformationEvent (raw input layer).
            # NOTE: information_events stores bytes hash; we convert hex -> bytes.
            digest_bytes = bytes.fromhex(event.content_hash_sha256)
            observed_at = datetime.now(tz=UTC)

            canonical_url = None
            external_ref = None
            # Keep both in raw_payload; also try to map stable identifiers.
            rss_meta = (event.raw_metadata or {}).get("rss") if isinstance(event.raw_metadata, dict) else None
            if isinstance(rss_meta, dict):
                canonical_url = rss_meta.get("link")
                external_ref = rss_meta.get("external_id") or event.source_id

            stmt = pg_insert(InformationEvent).values(
                source_ref=event.source_name,
                external_ref=external_ref,
                canonical_url=canonical_url,
                title=(rss_meta.get("title") if isinstance(rss_meta, dict) else None) or None,
                body_excerpt=event.abstract,
                content_html=(event.raw_metadata.get("content_html") if isinstance(event.raw_metadata, dict) else None) or None,
                content_text=(event.raw_metadata.get("content_text") if isinstance(event.raw_metadata, dict) else None) or None,
                content_excerpt=(event.raw_metadata.get("content_excerpt") if isinstance(event.raw_metadata, dict) else None) or None,
                fetched_content_at=(event.raw_metadata.get("content_fetch_meta", {}).get("fetched_at") if isinstance(event.raw_metadata, dict) else None),
                content_fetch_status=(event.raw_metadata.get("content_fetch_meta", {}).get("status") if isinstance(event.raw_metadata, dict) else None),
                raw_payload=event.raw_metadata,
                content_hash_sha256=digest_bytes,
                event_time=_to_utc(event.event_time),
                observed_at=observed_at,
            )

            # IMPORTANT: isolate each insert with a SAVEPOINT to preserve partial success.
            # If a duplicate hits a unique constraint, we roll back only this insert.
            with db_session.begin_nested():
                result = db_session.execute(stmt)
                inserted = bool(getattr(result, "rowcount", 0))
                return inserted
        except IntegrityError:
            # Dedup or constraint violation: do not crash; treat as not inserted.
            return False
        except Exception:
            return False

