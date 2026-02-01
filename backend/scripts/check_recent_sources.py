from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

# Ensure `backend/` is on sys.path when run from repo root
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.db import SessionLocal
from app.models.information_event import InformationEvent


def main(hours: int = 24, top_n: int = 30):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    s = SessionLocal()
    try:
        q = (
            s.query(InformationEvent.source_ref)
            .filter(InformationEvent.observed_at >= cutoff)
            .with_entities(InformationEvent.source_ref, )
        )
        # Use raw SQL group by for efficiency
        from sqlalchemy import text

        rows = s.execute(
            text(
                "SELECT source_ref, COUNT(*) AS cnt"
                " FROM information_events"
                " WHERE observed_at >= :cutoff"
                " GROUP BY source_ref"
                " ORDER BY cnt DESC"
                " LIMIT :limit"
            ),
            {"cutoff": cutoff, "limit": top_n},
        ).fetchall()

        if not rows:
            print(f"No information_events in the last {hours} hours.")
            return

        print(f"Top {len(rows)} sources by information_events in last {hours} hours (observed_at >= {cutoff.isoformat()}):")
        for src, cnt in rows:
            print(f"- {src}: {cnt}")

    finally:
        s.close()


if __name__ == '__main__':
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument('--hours', type=int, default=24)
    p.add_argument('--top', type=int, default=30)
    args = p.parse_args()
    main(hours=args.hours, top_n=args.top)
