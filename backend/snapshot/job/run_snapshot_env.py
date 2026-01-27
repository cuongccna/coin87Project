from __future__ import annotations

"""Job C entry point: snapshot decision environment (immutable).

STRICT:
- READ decision_risk_events and narrative_clusters.
- INSERT (append-only) into decision_environment_snapshots.
- At most one snapshot per run.
- Do not insert if identical to last snapshot (material-change dedup).

Run:
  python snapshot/job/run_snapshot_env.py
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import select

# Ensure backend/ is importable as top-level `app`.
BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.env import load_env_if_present  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
import app.models as _models  # noqa: F401,E402
from app.models.decision_environment_snapshot import DecisionEnvironmentSnapshot, EnvironmentState  # noqa: E402
from snapshot.core.environment_evaluator import evaluate  # noqa: E402
from snapshot.core.risk_aggregator import aggregate  # noqa: E402


UTC = timezone.utc
logger = logging.getLogger("coin87.snapshot")
logger.setLevel(logging.INFO)
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def _log(event: dict) -> None:
    logger.info(json.dumps(event, ensure_ascii=False))


def _latest_snapshot(db) -> Optional[DecisionEnvironmentSnapshot]:
    stmt = select(DecisionEnvironmentSnapshot).order_by(DecisionEnvironmentSnapshot.snapshot_time.desc()).limit(1)
    return db.execute(stmt).scalars().first()


def _same_material_state(
    *,
    last: DecisionEnvironmentSnapshot,
    state: EnvironmentState,
    dominant_risks: list[str],
    risk_density: int,
) -> bool:
    return (
        str(last.environment_state) == str(state)
        and list(last.dominant_risks or []) == list(dominant_risks or [])
        and int(last.risk_density) == int(risk_density)
    )


def main() -> int:
    load_env_if_present()

    snapshot_time = datetime.now(tz=UTC)

    db = SessionLocal()
    try:
        sig = aggregate(db, snapshot_time=snapshot_time)
        last = _latest_snapshot(db)
        last_state = last.environment_state if last else None
        last_time = last.snapshot_time if last else None

        evaluated = evaluate(
            snapshot_time=snapshot_time,
            signals=sig,
            last_state=last_state,
            last_snapshot_time=last_time,
        )

        if last and _same_material_state(
            last=last,
            state=evaluated.environment_state,
            dominant_risks=evaluated.dominant_risks,
            risk_density=evaluated.risk_density,
        ):
            _log(
                {
                    "event": "snapshot_no_material_change",
                    "snapshot_created": False,
                    "snapshot_time": snapshot_time.isoformat(),
                    "environment_state": str(evaluated.environment_state),
                    "risk_density": evaluated.risk_density,
                    "dominant_risks": evaluated.dominant_risks,
                    "errors": 0,
                }
            )
            return 0

        snap = DecisionEnvironmentSnapshot(
            snapshot_time=snapshot_time,
            environment_state=evaluated.environment_state,
            dominant_risks=evaluated.dominant_risks,
            risk_density=evaluated.risk_density,
        )
        db.add(snap)
        db.commit()

        _log(
            {
                "event": "snapshot_created",
                "snapshot_created": True,
                "snapshot_time": snapshot_time.isoformat(),
                "environment_state": str(evaluated.environment_state),
                "risk_density": evaluated.risk_density,
                "dominant_risks": evaluated.dominant_risks,
                "errors": 0,
            }
        )
        return 0
    except Exception as ex:  # noqa: BLE001
        db.rollback()
        _log(
            {
                "event": "snapshot_failed",
                "snapshot_created": False,
                "snapshot_time": snapshot_time.isoformat(),
                "errors": 1,
                "error_type": type(ex).__name__,
            }
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

