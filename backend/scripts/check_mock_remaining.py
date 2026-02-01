from __future__ import annotations

from pathlib import Path
import sys

# Ensure `backend/` is on sys.path when run from repo root
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.db import SessionLocal
from app.models.information_event import InformationEvent


def main():
    s = SessionLocal()
    try:
        c = s.query(InformationEvent).filter(InformationEvent.source_ref.ilike('mock_source_%')).count()
        c2 = s.query(InformationEvent).filter(InformationEvent.raw_payload.contains({'mock': True})).count()
        print('remaining source_ref mock_source_ count:', c)
        print('remaining raw_payload mock:true count:', c2)
    finally:
        s.close()


if __name__ == '__main__':
    main()
