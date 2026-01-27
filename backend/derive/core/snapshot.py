"""Reliability History Snapshot Logic.

Captures and persists the reliability state of narrative clusters.
Enables time-series analysis of how information reliability evolves.

Coin87 Philosophy:
- Append-only history
- Auditability
- Future trend support
"""

from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Mapping

from sqlalchemy.orm import Session

from app.models.narrative_reliability_snapshot import NarrativeReliabilitySnapshot
from derive.core.aggregation import ClusterMetrics
from derive.core.reliability import ReliabilityResult


def create_reliability_snapshot(
    db: Session,
    metrics: ClusterMetrics,
    classification: ReliabilityResult,
    snapshot_time: datetime,
) -> NarrativeReliabilitySnapshot:
    """Create a single reliability history snapshot.
    
    Args:
        db: Database session
        metrics: Calculated cluster metrics (source data)
        classification: Derived reliability status and score
        snapshot_time: Timestamp for the snapshot
        
    Returns:
        The created snapshot object (not committed yet)
    """
    
    # Convert metrics to dict for storage
    # using dataclasses.asdict but handling datetime serialization if needed
    # (JSONB handles ISO strings usually, but manual conversion is safer)
    metrics_dict = {
        "event_count": metrics.event_count,
        "source_count": metrics.source_count,
        "source_diversity_count": metrics.source_diversity_count,
        "lifespan_minutes": metrics.lifespan_minutes,
        "remention_rate_per_hour": metrics.remention_rate_per_hour,
        "first_seen": metrics.first_seen.isoformat(),
        "last_seen": metrics.last_seen.isoformat(),
    }

    snapshot = NarrativeReliabilitySnapshot(
        id=uuid.uuid4(),
        cluster_id=metrics.cluster_id,
        snapshot_at=snapshot_time,
        reliability_status=classification.status,
        reliability_score=classification.score,
        metrics_snapshot=metrics_dict,
        reasoning_snapshot=classification.reasoning
    )
    
    db.add(snapshot)
    return snapshot


def capture_batch_snapshots(
    db: Session,
    cluster_results: Mapping[uuid.UUID, tuple[ClusterMetrics, ReliabilityResult]],
) -> int:
    """Capture snapshots for a batch of clusters.
    
    Args:
        db: Database session
        cluster_results: Map of cluster_id -> (metrics, classification)
        
    Returns:
        Number of snapshots created
    """
    now = datetime.now(timezone.utc)
    count = 0
    
    for _, (metrics, classification) in cluster_results.items():
        create_reliability_snapshot(
            db=db,
            metrics=metrics,
            classification=classification,
            snapshot_time=now
        )
        count += 1
        
    return count
