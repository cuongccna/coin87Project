from __future__ import annotations

"""Job A entry point: fetch/collect -> normalize -> dedup -> insert into information_events.

STRICT:
- Only inserts into information_events (append-only).
- Never touches derived tables.
- No business logic, no scoring, no risk evaluation.
- Failure isolated per source; partial ingestion is success.

Run:
  python ingestion/jobs/run_ingestion.py
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure `backend/` is on sys.path so `import app...` works when run from repo root.
BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.env import load_env_if_present  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from ingestion.adapters.reddit_adapter import RedditAdapter  # noqa: E402
from ingestion.adapters.rss_adapter import RssAdapter  # noqa: E402
from ingestion.adapters.telegram_adapter import TelegramAdapter  # noqa: E402
from ingestion.core.fetch_context import FetchContext  # noqa: E402
from ingestion.core.source_registry import load_sources_yaml  # noqa: E402


UTC = timezone.utc
logger = logging.getLogger("coin87.ingestion")
logger.setLevel(logging.INFO)

# Ensure logs are visible when run from Task Scheduler / console.
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def _log(event: dict) -> None:
    # Structured logs only; never log raw content.
    logger.info(json.dumps(event, ensure_ascii=False))


def main() -> int:
    load_env_if_present()

    # Config path: backend/ingestion/config/sources.yaml by default.
    cfg_path = os.environ.get("C87_SOURCES_YAML") or str(
        Path(__file__).resolve().parents[1] / "config" / "sources.yaml"
    )
    registry = load_sources_yaml(Path(cfg_path))

    adapters = {
        "rss": RssAdapter(),
        "github": RssAdapter(),  # GitHub releases use Atom; feedparser handles it.
        "telegram": TelegramAdapter(),
        "reddit": RedditAdapter(),
    }

    ctx = FetchContext()
    started_at = datetime.now(tz=UTC).isoformat()

    run_totals = {"sources": 0, "fetched": 0, "inserted": 0, "deduped": 0, "errors": 0}

    for source in registry.enabled_sources():
        run_totals["sources"] += 1
        adapter = adapters.get(source.type)
        if adapter is None:
            # Unknown type: skip silently.
            continue

        fetched_count = 0
        inserted_count = 0
        deduped_count = 0
        error_count = 0

        try:
            raw_items = adapter.fetch(ctx, source)
            fetched_count = len(raw_items)
            run_totals["fetched"] += fetched_count
        except Exception:  # noqa: BLE001
            # Adapter is responsible to swallow; we still isolate.
            error_count += 1

        # Insert within a single session per source.
        session = SessionLocal()
        try:
            for raw in raw_items:
                try:
                    ev = adapter.normalize(raw, source)
                    if ev is None:
                        error_count += 1
                        continue
                    if not adapter.validate(ev):
                        error_count += 1
                        continue
                    ok = adapter.insert(ev, session)
                    if ok:
                        inserted_count += 1
                    else:
                        deduped_count += 1
                except Exception:  # noqa: BLE001
                    error_count += 1
                    continue

            # Commit only inserts; if adapter did rollback on integrity error, commit is safe.
            session.commit()
        except Exception:  # noqa: BLE001
            session.rollback()
            error_count += 1
        finally:
            session.close()

        run_totals["inserted"] += inserted_count
        run_totals["deduped"] += deduped_count
        run_totals["errors"] += error_count

        _log(
            {
                "event": "ingestion_source_summary",
                "started_at": started_at,
                "source_key": source.key,
                "source_name": source.name or source.key,
                "source_type": source.type,
                "fetched_count": fetched_count,
                "inserted_count": inserted_count,
                "deduplicated_count": deduped_count,
                "error_count": error_count,
            }
        )

    _log(
        {
            "event": "ingestion_run_summary",
            "started_at": started_at,
            "sources_count": run_totals["sources"],
            "fetched_count": run_totals["fetched"],
            "inserted_count": run_totals["inserted"],
            "deduplicated_count": run_totals["deduped"],
            "error_count": run_totals["errors"],
        }
    )

    # Partial ingestion is success. Only fail if registry cannot be loaded (handled earlier).
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

