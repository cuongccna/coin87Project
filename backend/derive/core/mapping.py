"""Narrative mapper module.

Responsibility:
- Persist the results of AI clustering decisions.
- Create new NarrativeClusters when needed.
- Create ClusterAssignments to link events to clusters.
- Update NarrativeCluster stats (last_seen_at).

Coin87 Philosophy:
- Does NOT predict price.
- Does NOT generate trading signals.
- Evaluates INFORMATION RELIABILITY.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cluster_assignment import ClusterAssignment
from app.models.information_event import InformationEvent
from app.models.narrative_cluster import NarrativeCluster, NarrativeStatus
from derive.core.clustering import ClusteringResult, ClusterDecisionResult


def _get_or_create_cluster_by_id(
    db: Session,
    cluster_id: uuid.UUID
) -> Optional[NarrativeCluster]:
    """Retrieve existing cluster by ID (safeguard)."""
    return db.get(NarrativeCluster, cluster_id)


def _create_new_cluster(
    db: Session,
    theme: str,
    first_seen: datetime
) -> NarrativeCluster:
    """Create a new narrative cluster."""
    cluster = NarrativeCluster(
        id=uuid.uuid4(),
        theme=theme.strip(),
        first_seen_at=first_seen,
        last_seen_at=first_seen,
        saturation_level=1,
        status=NarrativeStatus.ACTIVE,
    )
    db.add(cluster)
    db.flush()  # Generate ID and enforce constraints
    return cluster


def _update_cluster_stats(
    cluster: NarrativeCluster,
    seen_at: datetime
) -> None:
    """Update cluster timestamps and status."""
    if seen_at > cluster.last_seen_at:
        cluster.last_seen_at = seen_at
    
    # Reactivate if dormant
    if cluster.status != NarrativeStatus.ACTIVE:
        cluster.status = NarrativeStatus.ACTIVE
        # potentially increment saturation or reset parameters if needed
        # For now, minimal mutation rule applies.


def map_event_to_cluster(
    db: Session,
    event: InformationEvent,
    result: ClusteringResult
) -> Optional[ClusterAssignment]:
    """Apply clustering result to database.

    Logic:
    1. If ignore/noise, do nothing -> return None.
    2. If EXISTING_CLUSTER:
       - Validate cluster exists.
       - Update cluster last_seen_at.
       - Insert assignment.
    3. If NEW_CLUSTER:
       - Create new NarrativeCluster.
       - Insert assignment.
    
    Args:
        db: Active DB session
        event: The InformationEvent (must be already inserted/attached)
        result: The AI decision
        
    Returns:
        The created ClusterAssignment, or None if skipped/noise.
        Raises ValueError if logic invalid (e.g. mapping to non-existent cluster).
    """
    if result.decision == ClusterDecisionResult.IGNORE_NOISE:
        return None

    target_cluster: Optional[NarrativeCluster] = None

    if result.decision == ClusterDecisionResult.EXISTING_CLUSTER:
        if not result.cluster_id:
            raise ValueError("EXISTING_CLUSTER decision missing cluster_id")
            
        target_cluster = _get_or_create_cluster_by_id(db, result.cluster_id)
        if not target_cluster:
            # Fallback: if AI hallucinated an ID, or ID was deleted (shouldn't happen).
            # Treat as NEW_CLUSTER if we have a topic, or fail.
            if result.new_topic:
                 # Fallback to creating new using the topic if available
                 target_cluster = _create_new_cluster(db, result.new_topic, event.observed_at)
            else:
                 raise ValueError(f"Target cluster {result.cluster_id} not found")
        else:
             _update_cluster_stats(target_cluster, event.observed_at)
             
    elif result.decision == ClusterDecisionResult.NEW_CLUSTER:
        if not result.new_topic:
            raise ValueError("NEW_CLUSTER decision missing new_topic")
            
        # Check if theme already exists to prevent duplicates (race condition handling)
        # In a real high-concurrency env, we'd need more complex locking or distinct constraints.
        # Here we do a quick check.
        existing = db.execute(
            select(NarrativeCluster).where(NarrativeCluster.theme == result.new_topic)
        ).scalars().first()
        
        if existing:
            target_cluster = existing
            _update_cluster_stats(target_cluster, event.observed_at)
        else:
            target_cluster = _create_new_cluster(db, result.new_topic, event.observed_at)

    if not target_cluster:
        raise RuntimeError("Failed to resolve target cluster for valid decision")

    # Create Assignment
    assignment = ClusterAssignment(
        information_event_id=event.id,
        cluster_id=target_cluster.id,
        confidence_score=result.confidence_score,
        is_manual_override=False
    )
    
    db.add(assignment)
    # We let caller commit or flush generally, but here we might flag modified objects.
    
    return assignment
