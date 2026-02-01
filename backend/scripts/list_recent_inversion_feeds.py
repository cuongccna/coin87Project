from __future__ import annotations

from pathlib import Path
import sys
import json

# Ensure `backend/` is on sys.path when run from repo root
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.db import SessionLocal
from app.models.inversion_feed import InversionFeed


def main(limit: int = 10):
    s = SessionLocal()
    try:
        items = (
            s.query(InversionFeed)
            .order_by(InversionFeed.created_at.desc())
            .limit(limit)
            .all()
        )
        out = []
        for it in items:
            out.append(
                {
                    "id": str(it.id),
                    "external_id": it.external_id,
                    "symbol": it.symbol,
                    "feed_type": it.feed_type,
                    "direction": it.direction,
                    "confidence": float(it.confidence) if it.confidence is not None else None,
                    "status": it.status,
                    "created_at": it.created_at.isoformat() if it.created_at else None,
                }
            )
        print(json.dumps(out, indent=2, ensure_ascii=False))
    finally:
        s.close()


if __name__ == '__main__':
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument('--limit', type=int, default=10)
    args = p.parse_args()
    main(limit=args.limit)
