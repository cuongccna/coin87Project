"""Reliability Evaluation Job.

Orchestrates the full pipeline:
1. Select active clusters
2. Aggregate information behavior metrics
3. Classify reliability based on rules
4. Update live cluster state
5. Capture historical snapshot

Coin87 Philosophy:
- Periodic evaluation (e.g., every 5-15 mins)
- Deterministic updates
- History preservation
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import db
from app.models.narrative_cluster import NarrativeCluster, NarrativeStatus
from derive.core.aggregation import (
    aggregate_cluster_metrics,
    update_cluster_saturation,
)
from derive.core.reliability import ReliabilityClassifier
from derive.core.snapshot import capture_batch_snapshots


def run_reliability_evaluation_job(session: Session) -> dict:
    """Execute the reliability evaluation pipeline."""
    
    # 1. Identify Active Clusters (Active or Fading)
    # Dormant clusters might be skipped to save resources, or evaluated less frequently
    stmt = select(NarrativeCluster.id).where(
        NarrativeCluster.status.in_([NarrativeStatus.ACTIVE, NarrativeStatus.FADING])
    )
    cluster_ids = list(session.execute(stmt).scalars().all())
    
    if not cluster_ids:
        return {"status": "no_active_clusters"}

    # 2. Aggregate Metrics
    metrics_map = aggregate_cluster_metrics(session, cluster_ids)
    
    # 3. Classify & Snapshot
    classifier = ReliabilityClassifier()
    results_map = {}
    
    for cid, metrics in metrics_map.items():
        classification = classifier.classify(metrics)
        results_map[cid] = (metrics, classification)
        
    # 4. Capture Snapshots
    snapshot_count = capture_batch_snapshots(session, results_map)
    
    # 5. Update Live State (Saturation)
    saturation_updates = update_cluster_saturation(session, metrics_map)
    
    session.commit()
    
    return {
        "status": "success",
        "evaluated_clusters": len(cluster_ids),
        "snapshots_created": snapshot_count,
        "saturation_updates": saturation_updates
    }


if __name__ == "__main__":
    # Local test runner
    # In production, this would be invoked by Celery or a cron script
    from app.core.db import SessionLocal
    
    db_session = SessionLocal()
    try:
        result = run_reliability_evaluation_job(db_session)
        print(f"Job Complete: {result}")
    finally:
        db_session.close()
