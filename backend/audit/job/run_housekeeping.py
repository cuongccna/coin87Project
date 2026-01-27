from __future__ import annotations

"""Job D entry point: housekeeping, audit & health report (READ-ONLY).

STRICT:
- Reads from DB only.
- Generates health_report.json and logs warnings.
- NO database writes.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure backend/ is importable as top-level `app`.
BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.env import load_env_if_present  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
import app.models as _models  # noqa: F401,E402
from audit.checks import (  # noqa: E402
    freshness_check,
    volume_check,
    enum_integrity_check,
    immutability_check,
    snapshot_consistency_check,
    re_evaluation_transparency_check,
)
from audit.report.health_report import Check, build_report, write_report  # noqa: E402


UTC = timezone.utc
logger = logging.getLogger("coin87.audit")
logger.setLevel(logging.INFO)
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def _log(event: dict) -> None:
    logger.info(json.dumps(event, ensure_ascii=False))


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    load_env_if_present()
    now = datetime.now(tz=UTC)

    # Conservative thresholds (minutes). Override via env if needed.
    ingest_max_age = int(os.environ.get("C87_AUDIT_INGEST_MAX_AGE_MIN", "360"))  # 6h
    derive_max_age = int(os.environ.get("C87_AUDIT_DERIVE_MAX_AGE_MIN", "360"))  # 6h
    snap_max_age = int(os.environ.get("C87_AUDIT_SNAPSHOT_MAX_AGE_MIN", "360"))  # 6h

    state_path = Path(__file__).resolve().parents[1] / "state" / "last_health_check.json"
    prev_state = _read_json(state_path)
    prev_baseline = prev_state.get("volume_baseline")

    checks: list[Check] = []
    warnings: list[str] = []

    db = SessionLocal()
    try:
        # Enforce read-only invariant at runtime.
        if db.new or db.dirty or db.deleted:
            _log({"event": "audit_failed", "error": "read_only_invariant_violated"})
            return 0

        st, details = freshness_check.run(
            db,
            now=now,
            ingest_max_age_minutes=ingest_max_age,
            derive_max_age_minutes=derive_max_age,
            snapshot_max_age_minutes=snap_max_age,
        )
        checks.append(Check(name="data_freshness_check", status=st, details=details))
        warnings.extend(details.get("warnings", []))
        _log({"event": "audit_check", "name": "data_freshness_check", "status": st})

        st, details, new_baseline = volume_check.run(db, now=now, baseline=prev_baseline)
        checks.append(Check(name="data_volume_sanity_check", status=st, details=details))
        warnings.extend(details.get("warnings", []))
        _log({"event": "audit_check", "name": "data_volume_sanity_check", "status": st})

        st, details = enum_integrity_check.run(db)
        checks.append(Check(name="enum_constraint_integrity_check", status=st, details=details))
        warnings.extend(details.get("warnings", []))
        _log({"event": "audit_check", "name": "enum_constraint_integrity_check", "status": st})

        st, details = immutability_check.run(db, now=now)
        checks.append(Check(name="immutability_safety_check", status=st, details=details))
        warnings.extend(details.get("warnings", []))
        _log({"event": "audit_check", "name": "immutability_safety_check", "status": st})

        st, details = snapshot_consistency_check.run(db, now=now)
        checks.append(Check(name="snapshot_consistency_check", status=st, details=details))
        warnings.extend(details.get("warnings", []))
        _log({"event": "audit_check", "name": "snapshot_consistency_check", "status": st})

        st, details = re_evaluation_transparency_check.run(db, now=now)
        checks.append(Check(name="re_evaluation_transparency_check", status=st, details=details))
        warnings.extend(details.get("warnings", []))
        _log({"event": "audit_check", "name": "re_evaluation_transparency_check", "status": st})

        recommended_actions = [
            "If freshness warnings exist: verify Task Scheduler jobs A/B/C are running and network egress is available.",
            "If integrity warnings exist: treat as governance incident; do not auto-fix. Investigate DB constraints and write paths.",
            "If immutability warning exists: consider adding DB-level audit triggers or retaining WAL for forensic review.",
        ]

        report = build_report(
            now=now,
            checks=checks,
            warnings=warnings,
            recommended_actions=recommended_actions,
        )

        out_path = Path(__file__).resolve().parents[1] / "report" / "health_report.json"
        write_report(out_path, report)

        # Update local state baseline (allowed; not a DB write).
        _write_json(
            state_path,
            {
                "last_run_time": now.isoformat(),
                "volume_baseline": new_baseline,
            },
        )

        _log({"event": "audit_report_written", "path": str(out_path)})
        return 0
    except Exception as ex:  # noqa: BLE001
        _log({"event": "audit_job_failed", "error_type": type(ex).__name__})
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

