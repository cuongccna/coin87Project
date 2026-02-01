from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Ensure `backend/` is on sys.path when run from repo root
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.db import SessionLocal
from app.models.information_event import InformationEvent
from app.models.decision_risk_event import DecisionRiskEvent, RiskType, RecommendedPosture


def make_hash(s: str) -> bytes:
    return hashlib.sha256(s.encode('utf-8')).digest()


def main():
    now = datetime.now(timezone.utc)
    session = SessionLocal()
    try:
        titles = [
            "Small community discussion about upcoming Layer-2 rollout",
            "Rumored partnership between exchange X and custody provider",
            "Social chatter: token Y potential airdrop",
            "Developer thread: minor consensus client upgrade discussion",
        ]

        inserted = 0
        for i, t in enumerate(titles):
            ie = InformationEvent(
                source_ref=f"mock_source_{i}",
                external_ref=None,
                canonical_url=None,
                title=t,
                body_excerpt=t + " — excerpt",
                raw_payload={"mock": True, "index": i},
                content_hash_sha256=make_hash(t),
                event_time=now - timedelta(hours=1 + i),
                observed_at=now - timedelta(hours=1 + i),
            )
            session.add(ie)
            session.flush()

            dre = DecisionRiskEvent(
                information_event_id=ie.id,
                risk_type=RiskType.NARRATIVE_CONTAMINATION,
                severity=1,
                affected_decisions=["trading"],
                recommended_posture=RecommendedPosture.REVIEW,
                detected_at=now - timedelta(hours=1 + i),
                valid_from=now - timedelta(hours=1 + i),
                valid_to=None,
            )
            session.add(dre)
            inserted += 1

        session.commit()
        print(f"Inserted {inserted} mock emerging items.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == '__main__':
    main()
