from __future__ import annotations

"""Re-evaluation transparency check (Job D).

Governance intent:
- Re-interpretation must be explicit and logged (re_evaluation_logs).
- Detect conditions where narratives appear active but no re-evaluation logs exist,
  reducing auditability.

Limitations:
- Without narrative history tables, we cannot prove whether a narrative changed
  "materially" without a log. We therefore check for presence/absence patterns
  and warn conservatively.
"""

from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.narrative_cluster import NarrativeCluster, NarrativeStatus
from app.models.re_evaluation_log import ReEvaluationLog


def run(db: Session, *, now: datetime) -> tuple[str, dict]:
    status = "OK"
    warnings: list[str] = []

    def warn(level: str, msg: str) -> None:
        nonlocal status
        warnings.append(msg)
        if level == "CRITICAL":
            status = "CRITICAL"
        elif level == "DEGRADED" and status != "CRITICAL":
            status = "DEGRADED"

    narratives_total = db.execute(select(func.count()).select_from(NarrativeCluster)).scalar_one()
    active_high = db.execute(
        select(func.count())
        .select_from(NarrativeCluster)
        .where(NarrativeCluster.status == NarrativeStatus.ACTIVE, NarrativeCluster.saturation_level >= 4)
    ).scalar_one()

    # Re-evaluation logs for narratives in the last 30 days.
    window_start = now - timedelta(days=30)
    reeval_narr_30d = db.execute(
        select(func.count())
        .select_from(ReEvaluationLog)
        .where(
            ReEvaluationLog.entity_type == "narrative_clusters",
            ReEvaluationLog.re_evaluated_at >= window_start,
        )
    ).scalar_one()

    if int(narratives_total) > 0 and int(reeval_narr_30d) == 0:
        warn(
            "DEGRADED",
            "Narrative clusters exist but no narrative re_evaluation_logs found in last 30 days; "
            "reinterpretation transparency cannot be demonstrated.",
        )

    if int(active_high) > 0 and int(reeval_narr_30d) == 0:
        warn(
            "DEGRADED",
            "High-saturation ACTIVE narratives detected without recent re_evaluation_logs; "
            "review narrative governance practices.",
        )

    details = {
        "narrative_clusters_total": int(narratives_total),
        "active_high_saturation_count": int(active_high),
        "re_evaluation_logs_narratives_30d": int(reeval_narr_30d),
        "warnings": warnings,
    }
    return status, details

