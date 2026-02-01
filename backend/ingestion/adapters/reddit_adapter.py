from __future__ import annotations

"""Reddit adapter for Job A (Free API via PRAW).

Scope:
- Fetch posts from configured subreddits using PRAW (Reddit's free API).
- Normalize into NormalizedEvent.
- Validate minimal fields.
- Insert append-only into information_events with ignore-on-conflict.

Free API Strategy:
- Uses Reddit OAuth2 (free tier: 60 requests/minute).
- Fetches top/hot posts from crypto-related subreddits.
- No aggressive polling (respects rate limits).
- Supports proxy for IP rotation if needed.

Non-goals:
- No scoring, classification, or risk evaluation.
- No updates to existing rows.
"""

import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

import praw
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.information_event import InformationEvent
from ingestion.core.adapter import BaseAdapter, NormalizedEvent, RawItem
from ingestion.core.dedup import compute_content_hash_sha256_bytes, compute_content_hash_sha256_hex
from ingestion.core.fetch_context import FetchContext, SourceConfig
from ingestion.core.content_fetcher import fetch_and_extract


UTC = timezone.utc


def _strip_markdown(text: str) -> str:
    """Remove basic markdown formatting."""
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Links
    text = re.sub(r'[*_~`]', '', text)  # Bold, italic, strikethrough, code
    text = re.sub(r'\n{2,}', '\n', text)  # Multiple newlines
    return text.strip()


def _to_utc(timestamp: float) -> datetime:
    """Convert Unix timestamp to UTC datetime."""
    return datetime.fromtimestamp(timestamp, tz=UTC)


class RedditAdapter(BaseAdapter):
    adapter_type = "reddit"

    def __init__(self) -> None:
        """Initialize Reddit client with credentials from environment."""
        # Free Reddit API credentials (read-only access)
        self._client_id = os.environ.get("REDDIT_CLIENT_ID", "")
        self._client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "")
        self._user_agent = os.environ.get("REDDIT_USER_AGENT", "coin87:v1.0 (by /u/coin87bot)")
        
    def _create_reddit_client(self) -> praw.Reddit | None:
        """Create PRAW Reddit instance with error handling."""
        if not self._client_id or not self._client_secret:
            return None
        
        try:
            reddit = praw.Reddit(
                client_id=self._client_id,
                client_secret=self._client_secret,
                user_agent=self._user_agent,
                requestor_kwargs={"timeout": 15},
            )
            # Test connection
            reddit.user.me()
            return reddit
        except Exception:  # noqa: BLE001
            return None

    def fetch(self, context: FetchContext, source: SourceConfig) -> list[RawItem]:
        """Fetch posts from Reddit subreddit.
        
        Source URL format: reddit://r/{subreddit}?limit={limit}&sort={hot|new|top}
        Example: reddit://r/cryptocurrency?limit=25&sort=hot
        """
        try:
            reddit = self._create_reddit_client()
            if reddit is None:
                # Fallback: use Reddit public JSON endpoints when PRAW credentials missing.
                try:
                    # Parse query parameters (limit, sort) from source.url
                    url_parts = source.url.replace("reddit://r/", "").split("?")
                    subreddit_name = url_parts[0] if url_parts else "cryptocurrency"
                    limit = 25
                    sort = "hot"
                    if len(url_parts) > 1:
                        params = dict(p.split("=") for p in url_parts[1].split("&") if "=" in p)
                        limit = int(params.get("limit", 25))
                        sort = params.get("sort", "hot")

                    json_sort = "hot" if sort == "hot" else ("new" if sort == "new" else "top")
                    json_url = f"https://reddit.com/r/{subreddit_name}/{json_sort}.json?limit={limit}"

                    temp_source = SourceConfig(
                        key=f"{source.key}_json_fallback",
                        enabled=True,
                        type=source.type,
                        url=json_url,
                        rate_limit_seconds=source.rate_limit_seconds,
                        proxy=source.proxy,
                        priority=source.priority,
                        name=source.name,
                    )

                    status_code, text, meta = context.fetch_text(source=temp_source)
                    if status_code != 200 or not text:
                        return []

                    import json as _json

                    js = _json.loads(text)
                    posts = js.get("data", {}).get("children", [])

                    context.mark_fetched(source)

                    items: list[RawItem] = []
                    for post in posts:
                        d = post.get("data", {})
                        if d.get("stickied"):
                            continue

                        payload = {
                            "id": d.get("id"),
                            "title": d.get("title"),
                            "selftext": d.get("selftext"),
                            "url": d.get("url"),
                            "permalink": f"https://reddit.com{d.get('permalink')}",
                            "author": d.get("author") or "[deleted]",
                            "score": d.get("score"),
                            "num_comments": d.get("num_comments"),
                            "created_utc": d.get("created_utc"),
                            "subreddit": subreddit_name,
                            "is_self": d.get("is_self"),
                        }
                        # detailed fetch if enabled
                        try:
                            link_val = payload.get("permalink") or payload.get("url")
                            if link_val and getattr(source, "detailed_fetch", False):
                                html, text, meta = fetch_and_extract(str(link_val), context, source.key)
                                if html is not None:
                                    payload["content_html"] = html
                                if text is not None:
                                    payload["content_text"] = text
                                if meta and meta.get("excerpt"):
                                    payload["content_excerpt"] = meta.get("excerpt")
                                payload["content_fetch_meta"] = meta
                        except Exception:
                            pass

                        items.append(RawItem(source_key=source.key, payload=payload))

                    return items
                except Exception:  # noqa: BLE001
                    return []

            # Parse source URL
            url_parts = source.url.replace("reddit://r/", "").split("?")
            subreddit_name = url_parts[0] if url_parts else "cryptocurrency"
            
            # Parse query parameters
            limit = 25
            sort = "hot"
            if len(url_parts) > 1:
                params = dict(p.split("=") for p in url_parts[1].split("&") if "=" in p)
                limit = int(params.get("limit", 25))
                sort = params.get("sort", "hot")

            # Respect rate limiting
            context.rate_limit_sleep_if_needed(source)
            context.jitter_sleep()

            # Fetch posts
            subreddit = reddit.subreddit(subreddit_name)
            posts = []
            
            if sort == "hot":
                posts = list(subreddit.hot(limit=limit))
            elif sort == "new":
                posts = list(subreddit.new(limit=limit))
            elif sort == "top":
                posts = list(subreddit.top(time_filter="day", limit=limit))

            context.mark_fetched(source)

            # Convert to RawItems
            items: list[RawItem] = []
            for post in posts:
                # Skip pinned/stickied posts
                if post.stickied:
                    continue
                
                payload = {
                    "id": post.id,
                    "title": post.title,
                    "selftext": post.selftext,
                    "url": post.url,
                    "permalink": f"https://reddit.com{post.permalink}",
                    "author": str(post.author) if post.author else "[deleted]",
                    "score": post.score,
                    "num_comments": post.num_comments,
                    "created_utc": post.created_utc,
                    "subreddit": subreddit_name,
                    "is_self": post.is_self,
                }
                # detailed fetch if enabled
                try:
                    link_val = payload.get("permalink") or payload.get("url")
                    if link_val and getattr(source, "detailed_fetch", False):
                        html, text, meta = fetch_and_extract(str(link_val), context, source.key)
                        if html is not None:
                            payload["content_html"] = html
                        if text is not None:
                            payload["content_text"] = text
                        if meta and meta.get("excerpt"):
                            payload["content_excerpt"] = meta.get("excerpt")
                        payload["content_fetch_meta"] = meta
                except Exception:
                    pass

                items.append(RawItem(source_key=source.key, payload=payload))
            
            return items

        except Exception:  # noqa: BLE001
            # Adapter swallows exceptions per contract
            return []

    def normalize(self, raw_item: RawItem, source: SourceConfig) -> Optional[NormalizedEvent]:
        """Normalize Reddit post into NormalizedEvent."""
        try:
            p = raw_item.payload
            title = str(p.get("title", "")).strip()
            selftext = str(p.get("selftext", "")).strip()
            post_id = str(p.get("id", "")).strip()
            permalink = str(p.get("permalink", "")).strip()
            
            # Build abstract: title + selftext preview
            abstract = title
            if selftext and len(selftext) > 10:
                clean_text = _strip_markdown(selftext)
                preview = clean_text[:300] + "..." if len(clean_text) > 300 else clean_text
                abstract = f"{title}. {preview}" if title else preview
            
            abstract = abstract.strip()
            if len(abstract) > 2000:
                abstract = abstract[:2000].rstrip()
            
            if not abstract:
                return None

            source_name = source.name or source.key
            
            # Content hash for deduplication
            h_hex = compute_content_hash_sha256_hex(abstract=abstract, source_name=source_name)

            # Metadata
            raw_metadata: dict[str, Any] = {
                "source_key": source.key,
                "source_type": source.type,
                "source_name": source_name,
                "url": source.url,
                "reddit": {
                    "id": post_id,
                    "title": title,
                    "permalink": permalink,
                    "url": p.get("url"),
                    "author": p.get("author"),
                    "score": p.get("score"),
                    "num_comments": p.get("num_comments"),
                    "subreddit": p.get("subreddit"),
                    "is_self": p.get("is_self"),
                },
            }

            # Event time from Reddit timestamp
            event_time = _to_utc(float(p.get("created_utc", 0)))
            
            # Source ID: Reddit post ID
            source_id = post_id or h_hex

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
        """Validate normalized event has minimum required fields."""
        return bool(
            event.source_id
            and event.source_name
            and event.abstract
            and len(event.abstract) > 10
            and event.content_hash_sha256
        )

    def insert(self, event: NormalizedEvent, db_session: Session) -> bool:
        """Insert into information_events with deduplication."""
        try:
            digest_bytes = bytes.fromhex(event.content_hash_sha256)
            observed_at = datetime.now(tz=UTC)

            # Extract Reddit metadata
            reddit_meta = (event.raw_metadata or {}).get("reddit") if isinstance(event.raw_metadata, dict) else None
            canonical_url = None
            external_ref = None
            title = None
            
            if isinstance(reddit_meta, dict):
                canonical_url = reddit_meta.get("permalink")
                external_ref = reddit_meta.get("id")
                title = reddit_meta.get("title")

            stmt = pg_insert(InformationEvent).values(
                source_ref=event.source_name,
                external_ref=external_ref,
                canonical_url=canonical_url,
                title=title,
                body_excerpt=event.abstract,
                content_html=(event.raw_metadata.get("content_html") if isinstance(event.raw_metadata, dict) else None) or None,
                content_text=(event.raw_metadata.get("content_text") if isinstance(event.raw_metadata, dict) else None) or None,
                content_excerpt=(event.raw_metadata.get("content_excerpt") if isinstance(event.raw_metadata, dict) else None) or None,
                fetched_content_at=(event.raw_metadata.get("content_fetch_meta", {}).get("fetched_at") if isinstance(event.raw_metadata, dict) else None),
                content_fetch_status=(event.raw_metadata.get("content_fetch_meta", {}).get("status") if isinstance(event.raw_metadata, dict) else None),
                raw_payload=event.raw_metadata,
                content_hash_sha256=digest_bytes,
                event_time=event.event_time,
                observed_at=observed_at,
            )

            # Isolate insert with SAVEPOINT for partial success
            with db_session.begin_nested():
                result = db_session.execute(stmt)
                inserted = bool(getattr(result, "rowcount", 0))
                return inserted

        except IntegrityError:
            # Duplicate - not an error
            return False
        except Exception:  # noqa: BLE001
            return False

