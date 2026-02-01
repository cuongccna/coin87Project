from __future__ import annotations
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import delete
from app.core.db import SessionLocal
from app.models.inversion_feed import InversionFeed

def main():
    s = SessionLocal()
    try:
        print("Deleting all entries from inversion_feeds...")
        s.execute(delete(InversionFeed))
        s.commit()
        print("Done.")
    except Exception as e:
        print(f"Error: {e}")
        s.rollback()
    finally:
        s.close()

if __name__ == "__main__":
    main()
