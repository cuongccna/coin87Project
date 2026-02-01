from __future__ import annotations

from pathlib import Path
import sys

# Ensure `backend/` is on sys.path when run from repo root
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.db import SessionLocal
from app.models.information_event import InformationEvent


def main(dry_run: bool = False):
    s = SessionLocal()
    try:
        items = s.query(InformationEvent).filter(InformationEvent.source_ref.ilike('mock_source_%')).all()
        if not items:
            print('No information_events with mock_source_ prefix found.')
            return
        print(f'Found {len(items)} InformationEvent(s) to rename source_ref for.')
        for ie in items:
            new_ref = f'removed_mock_{ie.id}'
            print(f"Will rename {ie.id} source_ref '{ie.source_ref}' -> '{new_ref}'")
            if not dry_run:
                ie.source_ref = new_ref
                ie.title = f"[REMOVED MOCK] {ie.title}"
                s.add(ie)
        if dry_run:
            print('Dry run complete.')
            return
        s.commit()
        print('Committed renames.')
    finally:
        s.close()


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    main(dry_run=args.dry_run)
