"""Narrative Lifecycle Management (Phase 6).

Tracks how information themes emerge, persist, and fade.
Manages the state machine for the 'Narrative' entity.

Rules:
- Deterministic transitions.
- Based on event velocity and duration.
- STRICTLY ignores market/price data.

"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import func, select, desc
from sqlalchemy.orm import Session

from app.models.cluster_assignment import ClusterAssignment
from app.models.information_event import InformationEvent
from app.models.narrative import Narrative, NarrativeMetrics, NarrativeState
from app.models.narrative_cluster import NarrativeCluster
from audit.core.tracer import log_narrative_state_change

logger = logging.getLogger(__name__)

UTC = timezone.utc

# Configuration (Locked)
VELOCITY_WINDOW_HOURS = 24
ACTIVE_VELOCITY_THRESHOLD = 0.5  # Mentions per hour
FADING_VELOCITY_THRESHOLD = 0.1
DORMANT_DAYS = 7  # If no activity for 7 days -> Dormant


def run_lifecycle_update(db: Session, dry_run: bool = False) -> dict:
    """Main entry point for lifecycle tracking."""
    logger.info("Starting Narrative Lifecycle Update.")
    
    # 1. Map Unlinked Clusters to Narratives
    mapped_count = _map_clusters_to_narratives(db)
    
    # 2. Update Metrics & State for All Non-Dormant Narratives
    updated_count = _update_narrative_states(db)
    
    if not dry_run:
        db.commit()
        
    return {
        "mapped_clusters": mapped_count,
        "updated_narratives": updated_count
    }


def _map_clusters_to_narratives(db: Session) -> int:
    """Ensure every NarrativeCluster is linked to a Narrative."""
    # Find clusters with no narrative_id
    stmt = select(NarrativeCluster).where(NarrativeCluster.narrative_id.is_(None))
    clusters = db.execute(stmt).scalars().all()
    
    count = 0
    for cluster in clusters:
        # Strategy:
        # 1. Look for existing Narrative with same 'theme'.
        # 2. If found, link.
        # 3. Else, create new Narrative.
        
        existing_narrative = db.execute(
            select(Narrative).where(Narrative.topic == cluster.theme)
        ).scalar_one_or_none()
        
        if existing_narrative:
            cluster.narrative_id = existing_narrative.id
            # Update narrative timestamps if needed
            if cluster.first_seen_at < existing_narrative.first_seen_at:
                existing_narrative.first_seen_at = cluster.first_seen_at
            if cluster.last_seen_at > existing_narrative.last_seen_at:
                existing_narrative.last_seen_at = cluster.last_seen_at
        else:
            # Create new
            new_narrative = Narrative(
                id=uuid.uuid4(),
                topic=cluster.theme,
                current_state=NarrativeState.EMERGING,
                first_seen_at=cluster.first_seen_at,
                last_seen_at=cluster.last_seen_at
            )
            db.add(new_narrative)
            db.flush() # get ID
            cluster.narrative_id = new_narrative.id
            
        count += 1
        
    return count


def _update_narrative_states(db: Session) -> int:
    """Re-evaluate state for all active/emerging/fading narratives."""
    # We check everything not DORMANT (or check DORMANT periodically to see if they woke up?)
    # Actually, if a cluster pushes 'last_seen_at' into a dormant narrative, it might wake up.
    # But for now, let's iterate all Narratives where last_seen_at is recent-ish or state is not DORMANT.
    
    # Simple approach: Check all narratives modified recently?
    # Better: Check all narratives that are NOT Dormant, PLUS any Dormant ones that had new activity.
    # For simplicity: Iterate all narratives that are NOT Dormant.
    
    stmt = select(Narrative).where(Narrative.current_state != NarrativeState.DORMANT)
    active_narratives = db.execute(stmt).scalars().all()
    
    # Also include DORMANT ones that have recent 'last_seen_at' (reactivation)
    # This happens if _map_clusters update last_seen_at.
    # (The mapping logic above updates timestamps).
    
    # We can just check ALL narratives? If count is high, filter.
    # Let's check narratives updated recently.
    
    count = 0
    for narrative in active_narratives:
        _evaluate_single_narrative(db, narrative)
        count += 1
        
    return count


def _evaluate_single_narrative(db: Session, narrative: Narrative):
    """Compute metrics and transition state."""
    
    now = datetime.now(UTC)
    
    # 1. Compute Metrics
    # Velocity: Mentions in last X hours.
    window_start = now - timedelta(hours=VELOCITY_WINDOW_HOURS)
    
    # Join Narrative -> NarrativeCluster -> ClusterAssignment -> InformationEvent
    # Count assignments created_at >= window_start
    velocity_stmt = (
        select(func.count(ClusterAssignment.information_event_id))
        .join(NarrativeCluster, ClusterAssignment.cluster_id == NarrativeCluster.id)
        .where(NarrativeCluster.narrative_id == narrative.id)
        .where(ClusterAssignment.created_at >= window_start)
    )
    mentions_in_window = db.execute(velocity_stmt).scalar() or 0
    velocity = mentions_in_window / VELOCITY_WINDOW_HOURS
    
    # Update last_seen from clusters (refresh)
    last_seen_stmt = (
        select(func.max(NarrativeCluster.last_seen_at))
        .where(NarrativeCluster.narrative_id == narrative.id)
    )
    latest_seen = db.execute(last_seen_stmt).scalar()
    if latest_seen and latest_seen > narrative.last_seen_at:
        narrative.last_seen_at = latest_seen
        
    # Active Duration
    duration_delta = narrative.last_seen_at - narrative.first_seen_at
    active_duration_minutes = duration_delta.total_seconds() / 60.0
    
    # 2. Determine State
    old_state = narrative.current_state
    new_state = old_state
    
    hours_since_last_seen = (now - narrative.last_seen_at).total_seconds() / 3600.0
    days_since_last_seen = hours_since_last_seen / 24.0
    
    # State Logic
    if old_state == NarrativeState.DORMANT:
        # Check for re-awakening
        if days_since_last_seen < 1: # Activity in last 24h
            new_state = NarrativeState.EMERGING # Start over as emerging? Or Jump to Active?
            # If velocity is high, jump to active
            if velocity > ACTIVE_VELOCITY_THRESHOLD:
                new_state = NarrativeState.ACTIVE
            else:
                new_state = NarrativeState.EMERGING
                
    elif old_state == NarrativeState.EMERGING:
        if velocity >= ACTIVE_VELOCITY_THRESHOLD:
            new_state = NarrativeState.ACTIVE
        elif days_since_last_seen > DORMANT_DAYS:
            new_state = NarrativeState.DORMANT
            
    elif old_state == NarrativeState.ACTIVE:
        if velocity < FADING_VELOCITY_THRESHOLD:
            # Check saturation vs fading
            # If duration is long, maybe SATURATED?
            # "SATURATED -> still present but no longer expanding"
            # Saturation usually implies high count but potentially slowing acceleration.
            # Simple rule: If velocity drops, check duration.
            new_state = NarrativeState.FADING
        elif duration_delta.days > 3 and velocity > ACTIVE_VELOCITY_THRESHOLD:
             # Long running high velocity -> Saturated? 
             # Or Saturated means "everyone knows".
             new_state = NarrativeState.SATURATED

    elif old_state == NarrativeState.SATURATED:
         if velocity < FADING_VELOCITY_THRESHOLD:
             new_state = NarrativeState.FADING
             
    elif old_state == NarrativeState.FADING:
        if velocity > ACTIVE_VELOCITY_THRESHOLD:
            new_state = NarrativeState.ACTIVE # Resurrection
        elif days_since_last_seen > DORMANT_DAYS:
            new_state = NarrativeState.DORMANT

    # Audit Trace for State Change
    if old_state != new_state:
        trend = "STABLE"
        if new_state == NarrativeState.ACTIVE and old_state == NarrativeState.EMERGING:
            trend = "INCREASING"
        elif new_state == NarrativeState.FADING or new_state == NarrativeState.DORMANT:
            trend = "DECREASING"
            
        log_narrative_state_change(
            db,
            narrative_id=narrative.id,
            old_state=old_state.value if old_state else "UNKNOWN",
            new_state=new_state.value,
            velocity_trend=trend
        )

    # 3. Apply Update
    narrative.current_state = new_state
    
    # 4. Record Metrics Snapshot
    snapshot = NarrativeMetrics(
        narrative_id=narrative.id,
        mention_velocity=velocity,
        active_duration_minutes=active_duration_minutes,
        current_state=new_state,
        snapshot_at=now
    )
    db.add(snapshot)
