import sys
from pathlib import Path

# Add backend to path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.db import SessionLocal
from app.models.source_health import SourceHealth

def inspect():
    with SessionLocal() as db:
        states = db.query(SourceHealth).all()
        for s in states:
            print(f"[{s.source_id}] Status: {s.status}, Failures: {s.failure_count}, Next: {s.next_allowed_at}")

if __name__ == "__main__":
    inspect()
