
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# Add backend to sys.path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.db import SessionLocal
from app.models.source_health import SourceHealth

def reset_all_states():
    session = SessionLocal()
    try:
        print("Resetting all source health states...")
        
        # Update all records
        # Set status to HEALTHY, failure_count to 0, next_allowed_at to None (allow immediately)
        # We also might want to clear etag/last_modified if we want to force full fetch, 
        # but usually we just want to unblock the scheduling.
        # Let's clear scheduling blocks but keep conditional fetch tokens to avoid bandwidth waste 
        # unless user typically wants 'Force Fetch' implies "Fetch everything again". 
        # The user said "FORCE RESET ... so we can debug". Debugging usually implies checking if connection works.
        # If we keep etag, we might get 304 Not Modified, which is valid but might look like "fetching 0 items".
        # To be safe for debugging "why 0 items", clearing ETag is better.
        
        count = session.query(SourceHealth).update({
            SourceHealth.status: "HEALTHY",
            SourceHealth.failure_count: 0,
            SourceHealth.next_allowed_at: None,
            SourceHealth.etag: None,
            SourceHealth.last_modified: None
        })
        
        session.commit()
        print(f"Successfully reset state for {count} sources.")
        print("Run 'python ingestion/jobs/run_ingestion.py' to test now.")
        
    except Exception as e:
        print(f"Error resetting states: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        reset_all_states()
    else:
        confirmation = input("This will reset rate limits and conditional fetch tokens for all sources. Type 'yes' to proceed: ")
        if confirmation.lower() == 'yes':
            reset_all_states()
        else:
            print("Operation cancelled. Use --force to skip confirmation.")
