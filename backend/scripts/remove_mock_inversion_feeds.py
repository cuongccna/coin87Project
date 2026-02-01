from __future__ import annotations

from pathlib import Path
import sys

# Ensure `backend/` is on sys.path when run from repo root
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.db import SessionLocal
from app.models.inversion_feed import InversionFeed


def main(dry_run: bool = True):
    s = SessionLocal()
    try:
        items = s.query(InversionFeed).filter(InversionFeed.external_id.ilike('sample-%')).all()
        if not items:
            print('No inversion_feeds with external_id starting with "sample-" found.')
            return
        print(f'Found {len(items)} inversion_feed(s) to remove:')
        for it in items:
            print(f' - id={it.id} external_id={it.external_id} symbol={it.symbol} created_at={it.created_at}')

        if dry_run:
            print('Dry run: no rows will be deleted. Use --commit to perform deletion.')
            return

        # Delete
        ids = [it.id for it in items]
        s.query(InversionFeed).filter(InversionFeed.id.in_(ids)).delete(synchronize_session=False)
        s.commit()
        print(f'Deleted {len(ids)} inversion_feed(s).')
    finally:
        s.close()


if __name__ == '__main__':
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument('--commit', action='store_true', help='Actually delete rows (default: dry-run)')
    args = p.parse_args()
    main(dry_run=not args.commit)
