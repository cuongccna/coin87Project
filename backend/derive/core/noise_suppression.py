"""Noise Suppression Engine (Phase 7).

Identifies and mitigates low-quality information based on behavioral signals.
Strictly deterministic and explainable.

Rules:
1. Untrusted Single Source -> SUPPRESS
2. Dormant Echo -> SUPPRESS
3. Weak Reliability -> DEPRIORITIZE
4. Consistent Noise -> SUPPRESS

Constraints:
- No Content Analysis (Sentiment)
- No Market Data
- No Arbitrary Censorship
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, select, and_, desc, or_
from sqlalchemy.orm import Session

from app.models.cluster_assignment import ClusterAssignment
from app.models.cluster_visibility import ClusterVisibility, SuppressLevel
from app.models.information_event import InformationEvent
from app.models.narrative import Narrative, NarrativeState
from app.models.narrative_cluster import NarrativeCluster
from app.models.narrative_reliability_snapshot import NarrativeReliabilitySnapshot
from app.models.source_reliability import SourceReliability
from derive.core.reliability import ReliabilityStatus
from audit.core.tracer import log_noise_suppression_change

logger = logging.getLogger(__name__)

UTC = timezone.utc

# Configuration (Locked)
TRUST_THRESHOLD_LOW = 0.4
DORMANT_ECHO_LIFESPAN_HOURS = 1.0  # If dormant and short-lived -> Suppress


def run_noise_suppression(db: Session, dry_run: bool = False) -> dict:
    """Evaluate visibility for all active/relevant clusters."""
    logger.info("Starting Phase 7: Noise Suppression")
    
    # 1. Fetch Clusters to Evaluate
    # We evaluate anything updated recently OR never evaluated.
    # For simplicity, we can evaluate ALL active clusters + recent dormant ones.
    # Or just iterate all clusters that have evolved (check updated_at vs last_evaluated_at).
    # Here, we do a broad sweep of clusters active in last 7 days.
    
    since = datetime.now(UTC) - timedelta(days=7)
    stmt = select(NarrativeCluster).where(NarrativeCluster.last_seen_at >= since)
    clusters = db.execute(stmt).scalars().all()
    
    stats = {
        "processed": 0,
        "suppressed": 0,
        "deprioritized": 0,
        "none": 0
    }
    
    for cluster in clusters:
        # Evaluate
        level, code, desc_text = _evaluate_cluster_visibility(db, cluster)
        
        # Upsert Visibility
        _update_visibility(db, cluster.id, level, code, desc_text)
        
        stats["processed"] += 1
        if level == SuppressLevel.SUPPRESS:
            stats["suppressed"] += 1
        elif level == SuppressLevel.DEPRIORITIZE:
            stats["deprioritized"] += 1
        else:
            stats["none"] += 1
            
    if not dry_run:
        db.commit()
        
    return stats


def _evaluate_cluster_visibility(
    db: Session, 
    cluster: NarrativeCluster
) -> Tuple[SuppressLevel, str, str]:
    """Apply deterministic rules to determine suppression level."""
    
    # 1. Gather Context
    # A. Reliability Status (Latest)
    status_stmt = (
        select(NarrativeReliabilitySnapshot.reliability_status)
        .where(NarrativeReliabilitySnapshot.cluster_id == cluster.id)
        .order_by(desc(NarrativeReliabilitySnapshot.snapshot_timestamp))
        .limit(1)
    )
    reliability_status_str = db.execute(status_stmt).scalar()
    
    # B. Source Stats (Count & Trust)
    # Join Assignments -> Events -> SourceReliability
    # We need distinct sources count and their max trust index.
    
    source_stmt = (
        select(
            func.count(func.distinct(InformationEvent.source_ref)).label("source_count"),
            func.max(SourceReliability.trust_index).label("max_trust")
        )
        .join(ClusterAssignment, InformationEvent.id == ClusterAssignment.information_event_id)
        .join(SourceReliability, InformationEvent.source_ref == SourceReliability.source_ref, isouter=True) # outer join incase trust metric missing
        .where(ClusterAssignment.cluster_id == cluster.id)
    )
    source_stats = db.execute(source_stmt).one()
    source_count = source_stats.source_count or 0
    max_trust = source_stats.max_trust if source_stats.max_trust is not None else 0.5 # Default neutral
    
    # C. Lifespan
    lifespan_hours = (cluster.last_seen_at - cluster.first_seen_at).total_seconds() / 3600.0
    
    # D. Narrative State (if linked)
    narrative_state = None
    if cluster.narrative_id:
        narrative = db.get(Narrative, cluster.narrative_id)
        if narrative:
            narrative_state = narrative.current_state

    # 2. Apply Rules
    
    # Rule 1: Consistently NOISE + Low Trust + Single Source
    if reliability_status_str == ReliabilityStatus.NOISE.value:
        if source_count <= 1 and max_trust < TRUST_THRESHOLD_LOW:
            return (
                SuppressLevel.SUPPRESS, 
                "UNTRUSTED_SINGLE_SOURCE", 
                f"Noise status from single low-trust source ({max_trust})"
            )
        # Even if multiple sources, if all are low trust? (Not implemented, strict interpretation of rule 1)
        
        # Rule 4: Consistent Noise (Implicitly suppression if just NOISE?)
        # "Part of a narrative already in DORMANT state"
        # Let's say if just NOISE status generally -> DEPRIORITIZE at least?
        # User requirement: "IF reliability_status = NOISE ... → SUPPRESS" (Specific case)
        # What about general Noise? 
        return (
             SuppressLevel.DEPRIORITIZE, # Or SUPPRESS if we want to be strict on all NOISE
             "RELIABILITY_NOISE",
             "Cluster Classified as NOISE"
        )

    # Rule 2: Dormant Echo
    # IF narrative_state = DORMANT AND cluster_lifespan < threshold
    if narrative_state == NarrativeState.DORMANT:
        if lifespan_hours < DORMANT_ECHO_LIFESPAN_HOURS:
            return (
                SuppressLevel.SUPPRESS,
                "DORMANT_ECHO",
                f"Short-lived activity ({lifespan_hours:.1f}h) in DORMANT narrative"
            )

    # Rule 3: Weak Reliability
    if reliability_status_str == ReliabilityStatus.WEAK.value:
        return (
            SuppressLevel.DEPRIORITIZE,
            "WEAK_RELIABILITY",
            "Reliability indicates WEAK confirmation"
        )

    # Default
    return (SuppressLevel.NONE, "OK", "Cluster meets visibility standards")


def _update_visibility(
    db: Session, 
    cluster_id: uuid.UUID, 
    level: SuppressLevel, 
    code: str, 
    desc_text: str
):
    """Persist the decision."""
    vis = db.get(ClusterVisibility, cluster_id)
    if not vis:
        vis = ClusterVisibility(cluster_id=cluster_id)
        db.add(vis)
    
    # Audit Trace
    log_noise_suppression_change(
        db,
        cluster_id=cluster_id,
        old_level=vis.suppress_level.value if vis.suppress_level else "NONE",
        new_level=level.value,
        reason_code=code,
        description=desc_text
    )

    vis.suppress_level = level
    vis.reason_code = code
    vis.reason_description = desc_text
    # last_evaluated_at updates automatically via onupdate
