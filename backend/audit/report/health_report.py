from __future__ import annotations

"""Health report generator (Job D).

Output: health_report.json
No DB writes. No auto-fixes.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


UTC = timezone.utc
Overall = Literal["OK", "DEGRADED", "CRITICAL"]


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    status: Overall
    details: dict[str, Any]


def _worst(a: Overall, b: Overall) -> Overall:
    order = {"OK": 0, "DEGRADED": 1, "CRITICAL": 2}
    return a if order[a] >= order[b] else b


def build_report(*, now: datetime, checks: list[Check], warnings: list[str], recommended_actions: list[str]) -> dict:
    overall: Overall = "OK"
    for c in checks:
        overall = _worst(overall, c.status)

    return {
        "run_time": now.astimezone(UTC).isoformat(),
        "overall_status": overall,
        "checks": [{"name": c.name, "status": c.status, "details": c.details} for c in checks],
        "warnings": warnings,
        "recommended_actions": recommended_actions,
    }


def write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

