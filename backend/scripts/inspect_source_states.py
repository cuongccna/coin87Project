
import sys
import os
from pathlib import Path

# Add backend to sys.path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.db import SessionLocal
from app.models.source_health import SourceHealth
from datetime import datetime, timezone

def inspect_states():
    session = SessionLocal()
    try:
        states = session.query(SourceHealth).all()
        print(f"{'Source ID':<30} | {'Status':<10} | {'Next Allowed At':<30} | {'Failure Count'}")
        print("-" * 90)
        for s in states:
            next_allowed = s.next_allowed_at
            if next_allowed and next_allowed.tzinfo is None:
                next_allowed = next_allowed.replace(tzinfo=timezone.utc)
            
            print(f"{s.source_id:<30} | {s.status:<10} | {str(next_allowed):<30} | {s.failure_count}")
    finally:
        session.close()

if __name__ == "__main__":
    inspect_states()
