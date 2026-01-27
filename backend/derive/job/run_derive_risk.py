from __future__ import annotations

"""Job B entry point: derive decision-level risks from information_events.

STRICT:
- READ from information_events.
- INSERT (append-only) into decision_risk_events.
- INSERT (append-only) into narrative_memberships.
- CONTROLLED UPDATE narrative_clusters only (last_seen_at, saturation_level ±1, status).
- INSERT re_evaluation_logs when reinterpretation occurs (rules version changes).

MUST NOT:
- Modify/delete information_events.
- Modify/delete decision_risk_events.
- Call external APIs.
- Run inside FastAPI.

Run:
  python derive/job/run_derive_risk.py
"""

import json
import logging
import os
import sys
import uuid
import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

# Ensure `backend/` is importable as top-level `app`.
BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.env import load_env_if_present  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
import app.models as _models  # noqa: F401,E402  (register ORM classes deterministically)
from app.models.decision_risk_event import DecisionRiskEvent, RecommendedPosture, RiskType  # noqa: E402
from app.models.information_event import InformationEvent  # noqa: E402
from derive.core.context_window import Cursor, advance_cursor, default_cursor, fetch_new_information_events  # noqa: E402
from derive.core.narrative_engine import attach_membership, get_or_create_cluster  # noqa: E402
from derive.core.risk_detector import RiskHit, load_rules, detect_risks_for_event  # noqa: E402


UTC = timezone.utc
logger = logging.getLogger("coin87.derive")
logger.setLevel(logging.INFO)
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def _log(event: dict) -> None:
    logger.info(json.dumps(event, ensure_ascii=False))


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.utcoffset() is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _event_text(ev: InformationEvent) -> str:
    # Deterministic input surface: title + excerpt only (no sentiment).
    t = (ev.title or "").strip()
    e = (ev.body_excerpt or "").strip()
    return (t + "\n" + e).strip()


def _load_state(path: Path) -> dict:
    if not path.exists():
        return json.loads((BASE_DIR / "derive" / "state" / "last_processed.json").read_text(encoding="utf-8"))
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_cursor(state: dict) -> Cursor:
    try:
        last_observed_at = datetime.fromisoformat(state["last_observed_at"])
    except Exception:  # noqa: BLE001
        last_observed_at = default_cursor().last_observed_at
    if last_observed_at.tzinfo is None or last_observed_at.utcoffset() is None:
        last_observed_at = last_observed_at.replace(tzinfo=UTC)
    else:
        last_observed_at = last_observed_at.astimezone(UTC)

    try:
        last_id = uuid.UUID(state["last_id"])
    except Exception:  # noqa: BLE001
        last_id = default_cursor().last_id
    return Cursor(last_observed_at=last_observed_at, last_id=last_id)


def _write_state(path: Path, *, cursor: Cursor, rules_version: str | None) -> None:
    payload = {
        "last_observed_at": cursor.last_observed_at.isoformat(),
        "last_id": str(cursor.last_id),
        "rules_version": rules_version,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _risk_exists(db: Session, *, information_event_id: uuid.UUID, risk_type: RiskType) -> bool:
    stmt = select(DecisionRiskEvent.id).where(
        DecisionRiskEvent.information_event_id == information_event_id,
        DecisionRiskEvent.risk_type == risk_type,
    )
    return db.execute(stmt).first() is not None


def _insert_risk(
    db: Session,
    *,
    information_event_id: uuid.UUID,
    hit: RiskHit,
    detected_at: datetime,
) -> DecisionRiskEvent | None:
    # Prevent duplicate risk_type per information_event within Job B (deterministic dedup).
    if _risk_exists(db, information_event_id=information_event_id, risk_type=hit.risk_type):
        return None

    r = DecisionRiskEvent(
        information_event_id=information_event_id,
        risk_type=hit.risk_type,
        severity=int(hit.severity),
        affected_decisions=list(hit.affected_decisions),
        recommended_posture=hit.recommended_posture,
        detected_at=detected_at,
        valid_from=detected_at,
        valid_to=None,
    )
    db.add(r)
    db.flush()
    return r


def main() -> int:
    load_env_if_present()

    p = argparse.ArgumentParser(add_help=True)
    p.add_argument(
        "--replay-hours",
        type=int,
        default=0,
        help="Reprocess a recent window for diagnostics (dedup prevents duplicates). Does not change rules.",
    )
    p.add_argument(
        "--no-state-write",
        action="store_true",
        help="Do not persist cursor (useful with --replay-hours for diagnostics).",
    )
    args = p.parse_args()

    rules_dir = Path(__file__).resolve().parents[1] / "rules"
    rules = load_rules(
        narrative_path=rules_dir / "narrative_rules.yaml",
        timing_path=rules_dir / "timing_distortion_rules.yaml",
        consensus_path=rules_dir / "consensus_rules.yaml",
    )

    state_path = Path(__file__).resolve().parents[1] / "state" / "last_processed.json"
    state = _load_state(state_path)
    cursor = _parse_cursor(state)
    prev_rules_version = state.get("rules_version")

    detected_at = _utc_now()
    run_started_at = detected_at.isoformat()

    counters = {
        "events_processed": 0,
        "risks_created": 0,
        "narratives_updated": 0,
        "memberships_created": 0,
        "re_evaluations_logged": 0,
        "errors": 0,
    }

    seen_counts: dict[str, int] = {}

    db = SessionLocal()
    try:
        # Optional replay window for diagnostics (still deterministic; dedup avoids duplicate inserts).
        if args.replay_hours and args.replay_hours > 0:
            # Force to UTC and back up by replay window.
            cursor = Cursor(
                last_observed_at=_ensure_utc(detected_at) - timedelta(hours=int(args.replay_hours)),
                last_id=uuid.UUID(int=0),
            )

        # Process new events in bounded batches to stay scheduler-friendly.
        while True:
            batch = fetch_new_information_events(db, cursor=cursor, limit=200)
            if not batch:
                break

            for ev in batch:
                cursor = advance_cursor(cursor, ev)
                counters["events_processed"] += 1

                # Failure isolation per event.
                try:
                    text = _event_text(ev)
                    hits = detect_risks_for_event(text=text, rules=rules, seen_counts=seen_counts)
                    if not hits:
                        continue

                    # Nested transaction per event (savepoint); additional isolation inside for narrative linkage.
                    with db.begin_nested():
                        for hit in hits:
                            risk = _insert_risk(db, information_event_id=ev.id, hit=hit, detected_at=detected_at)
                            if risk is None:
                                continue
                            counters["risks_created"] += 1

                            # Narrative engine only for narrative contamination hits.
                            if hit.risk_type == RiskType.NARRATIVE_CONTAMINATION and hit.narrative_theme:
                                try:
                                    seen_at = _ensure_utc(ev.observed_at)
                                    cluster, created, reeval = get_or_create_cluster(
                                        db,
                                        theme=hit.narrative_theme,
                                        seen_at=seen_at,
                                        rules_version=rules.version,
                                        prev_rules_version=str(prev_rules_version) if prev_rules_version else None,
                                    )
                                    if created or reeval is not None:
                                        counters["narratives_updated"] += 1
                                    if reeval is not None:
                                        counters["re_evaluations_logged"] += 1

                                    if attach_membership(db, narrative_id=cluster.id, decision_risk_event_id=risk.id):
                                        counters["memberships_created"] += 1
                                except Exception as ex:  # noqa: BLE001
                                    counters["errors"] += 1
                                    _log(
                                        {
                                            "event": "derive_event_error",
                                            "stage": "narrative_link",
                                            "information_event_id": str(ev.id),
                                            "observed_at": str(getattr(ev, "observed_at", None)),
                                            "source_ref": (getattr(ev, "source_ref", "") or "")[:64],
                                            "title": (getattr(ev, "title", "") or "")[:120],
                                            "error_type": type(ex).__name__,
                                        }
                                    )
                                    # Continue; keep risk insert (do not abort entire event).
                                    continue
                except Exception as ex:  # noqa: BLE001
                    counters["errors"] += 1
                    _log(
                        {
                            "event": "derive_event_error",
                            "stage": "event_processing",
                            "information_event_id": str(ev.id),
                            "observed_at": str(getattr(ev, "observed_at", None)),
                            "source_ref": (getattr(ev, "source_ref", "") or "")[:64],
                            "title": (getattr(ev, "title", "") or "")[:120],
                            "error_type": type(ex).__name__,
                        }
                    )
                    continue

            db.commit()

        # Persist cursor only after DB commit.
        if not args.no_state_write:
            _write_state(state_path, cursor=cursor, rules_version=rules.version)
    finally:
        db.close()

    _log(
        {
            "event": "derive_run_summary",
            "started_at": run_started_at,
            "rules_version": rules.version,
            **counters,
        }
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

