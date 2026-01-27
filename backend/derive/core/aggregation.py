"""Batch aggregation logic for Narrative Clusters.

Computes information behavior metrics for clusters:
- Source count: Number of unique sources participating
- Source diversity: Number of unique source platforms (telegram, twitter, etc.)
- Lifespan: Duration of active discussion
- Remention rate: Velocity of new information events
- Contradiction count: (Placeholder for future sentiment/stance analysis)

Coin87 Philosophy:
- Information Reliability only
- No market data used
- pure SQL aggregation for performance
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.cluster_assignment import ClusterAssignment
from app.models.information_event import InformationEvent
from app.models.narrative_cluster import NarrativeCluster


@dataclass(frozen=True)
class ClusterMetrics:
    cluster_id: uuid.UUID
    event_count: int
    source_count: int
    source_diversity_count: int
    lifespan_minutes: float
    remention_rate_per_hour: float
    first_seen: datetime
    last_seen: datetime
    # contradiction_count: int = 0  # To be implemented with stance classification


def get_cluster_metrics_query(cluster_ids: list[uuid.UUID] = None):
    """Generate SQLAlchemy Core query for batch aggregation.
    
    Computes:
    - distinct source_ref count
    - distinct source type count (parsed from source_ref)
    - min/max observed_at
    - total event count
    """
    
    # Extract source_type from source_ref (format "type:id")
    # Postgres specific: split_part(string, delimiter, position)
    source_type_expr = func.split_part(InformationEvent.source_ref, ':', 1)
    
    # Lifespan in minutes
    # Postgres specific: extract(epoch from interval) / 60
    lifespan_expr = func.extract(
        'epoch', 
        func.max(InformationEvent.observed_at) - func.min(InformationEvent.observed_at)
    ) / 60.0

    stmt = (
        select(
            ClusterAssignment.cluster_id,
            func.count(InformationEvent.id).label("event_count"),
            func.count(func.distinct(InformationEvent.source_ref)).label("source_count"),
            func.count(func.distinct(source_type_expr)).label("source_diversity_count"),
            func.min(InformationEvent.observed_at).label("first_seen"),
            func.max(InformationEvent.observed_at).label("last_seen"),
            lifespan_expr.label("lifespan_minutes"),
        )
        .join(InformationEvent, ClusterAssignment.information_event_id == InformationEvent.id)
        .group_by(ClusterAssignment.cluster_id)
    )

    if cluster_ids:
        stmt = stmt.where(ClusterAssignment.cluster_id.in_(cluster_ids))

    return stmt


def aggregate_cluster_metrics(
    db: Session, 
    cluster_ids: list[uuid.UUID]
) -> dict[uuid.UUID, ClusterMetrics]:
    """Execute batch aggregation and return metrics objects.
    
    Args:
        db: Database session
        cluster_ids: List of cluster IDs to analyze
        
    Returns:
        Dictionary mapping cluster_id -> ClusterMetrics
    """
    if not cluster_ids:
        return {}

    stmt = get_cluster_metrics_query(cluster_ids)
    rows = db.execute(stmt).all()

    results = {}
    
    for row in rows:
        cid = row.cluster_id
        event_count = row.event_count
        lifespan_mins = float(row.lifespan_minutes or 0.0)
        
        # Calculate remention rate (events per hour)
        # Avoid division by zero for single-event clusters or <1 minute lifespan
        hours = lifespan_mins / 60.0
        if hours < 0.1:
            hours = 0.1 # Minimum floor to prevent explosion
            
        rate = event_count / hours

        metrics = ClusterMetrics(
            cluster_id=cid,
            event_count=event_count,
            source_count=row.source_count,
            source_diversity_count=row.source_diversity_count,
            lifespan_minutes=lifespan_mins,
            remention_rate_per_hour=round(rate, 2),
            first_seen=row.first_seen.replace(tzinfo=timezone.utc),
            last_seen=row.last_seen.replace(tzinfo=timezone.utc)
        )
        results[cid] = metrics

    return results


def update_cluster_saturation(db: Session, metrics: dict[uuid.UUID, ClusterMetrics]) -> int:
    """Update NarrativeCluster saturation levels based on computed metrics.
    
    Simple Heuristic Rule:
    - Level 1: < 3 sources
    - Level 2: 3-5 sources OR > 20 events
    - Level 3: > 5 sources AND > 2 types
    - Level 4: > 10 sources AND > 3 types
    - Level 5: > 20 sources OR > 100 events (Viral)
    
    This is an example of batch updating derived state.
    """
    updated_count = 0
    
    for cid, m in metrics.items():
        # Determine new saturation
        new_level = 1
        if m.source_count > 20 or m.event_count > 100:
            new_level = 5
        elif m.source_count > 10 and m.source_diversity_count > 3:
            new_level = 4
        elif m.source_count > 5 and m.source_diversity_count > 2:
            new_level = 3
        elif m.source_count >= 3 or m.event_count > 20:
            new_level = 2
            
        # Update DB
        # We fetch and update. In high-perf, use update() statement.
        cluster = db.get(NarrativeCluster, cid)
        if cluster and cluster.saturation_level != new_level:
            cluster.saturation_level = new_level
            updated_count += 1
            
    return updated_count
