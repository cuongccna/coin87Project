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
from app.models.decision_risk_event import DecisionRiskEvent


def main(dry_run: bool = False):
    session = SessionLocal()
    try:
        # Find InformationEvents inserted by the mock_emerging script
        mock_events = (
            session.query(InformationEvent)
            .filter(
                (InformationEvent.source_ref.ilike("mock_source_%"))
                | (InformationEvent.raw_payload.contains({"mock": True}))
            )
            .all()
        )

        if not mock_events:
            print("No mock information_events found.")
            return

        print(f"Found {len(mock_events)} mock InformationEvent(s).")

        updated_dr = 0
        updated_ie = 0

        now = datetime.now(timezone.utc)

        for ie in mock_events:
            # Close any open DecisionRiskEvent windows referencing this information event
            drs = (
                session.query(DecisionRiskEvent)
                .filter(DecisionRiskEvent.information_event_id == ie.id)
                .all()
            )

            for dr in drs:
                if dr.valid_to is None:
                    print(f"Will set valid_to for DecisionRiskEvent {dr.id} (detected_at={dr.detected_at})")
                    if not dry_run:
                        # Ensure UTC timezone for valid_to per model validators
                        # Ensure valid_to is strictly after valid_from to satisfy DB check
                        if dr.valid_from is not None:
                            dr.valid_to = dr.valid_from.astimezone(timezone.utc) + timedelta(seconds=1)
                        elif dr.detected_at is not None:
                            dr.valid_to = dr.detected_at.astimezone(timezone.utc)
                        else:
                            dr.valid_to = now
                        session.add(dr)
                    updated_dr += 1

            # Remove the mock flag from raw_payload (or mark removed)
            payload = dict(ie.raw_payload or {})
            if payload.pop("mock", None) is not None:
                payload["_mock_removed_at"] = now.isoformat()
                print(f"Will update InformationEvent {ie.id} raw_payload to remove 'mock' flag")
                if not dry_run:
                    ie.raw_payload = payload
                    session.add(ie)
                updated_ie += 1

        if dry_run:
            print(f"Dry run complete. DecisionRiskEvent to update: {updated_dr}, InformationEvent to update: {updated_ie}")
            return

        session.commit()
        print(f"Committed changes. DecisionRiskEvent updated: {updated_dr}, InformationEvent updated: {updated_ie}")

    except Exception as exc:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Cleanup mock emerging items (safe mode)")
    p.add_argument("--dry-run", action="store_true", help="Show what would be changed without committing")
    args = p.parse_args()

    main(dry_run=args.dry_run)
