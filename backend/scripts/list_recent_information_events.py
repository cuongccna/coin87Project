from __future__ import annotations

from pathlib import Path
import sys
import json

# Ensure `backend/` is on sys.path when run from repo root
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.db import SessionLocal
from app.models.information_event import InformationEvent


def main(limit: int = 10):
    s = SessionLocal()
    try:
        items = (
            s.query(InformationEvent)
            .order_by(InformationEvent.observed_at.desc())
            .limit(limit)
            .all()
        )
        out = []
        for it in items:
            out.append(
                {
                    "id": str(it.id),
                    "source_ref": it.source_ref,
                    "external_ref": it.external_ref,
                    "title": it.title,
                    "observed_at": it.observed_at.isoformat() if it.observed_at else None,
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
