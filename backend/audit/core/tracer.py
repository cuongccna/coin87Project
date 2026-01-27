"""Audit Trace Generator (Phase 9).

Central logic for creating explanation records for system decisions.
Ensures signals are qualitative and clear, never numeric/opaque.
"""

import logging
from typing import Optional, Dict, Any
import uuid

from sqlalchemy.orm import Session

from app.models.audit_trace import AuditTrace, AuditDecisionType

logger = logging.getLogger(__name__)


def log_reliability_change(
    db: Session,
    cluster_id: uuid.UUID,
    old_status: str,
    new_status: str,
    metrics_summary: Dict[str, Any]
):
    """Log a change in reliability classification."""
    if old_status == new_status:
        return

    # Convert numeric info to qualitative factors
    factors = _qualify_metrics(metrics_summary)
    factors["previous_status"] = old_status
    factors["new_status"] = new_status
    
    summary = f"Reliability status changed from {old_status} to {new_status} based on updated source confirmation patterns."
    
    _create_trace(
        db,
        cluster_id=cluster_id,
        decision_type=AuditDecisionType.RELIABILITY_CLASSIFICATION,
        summary=summary,
        factors=factors
    )


def log_noise_suppression_change(
    db: Session,
    cluster_id: uuid.UUID,
    old_level: str,
    new_level: str,
    reason_code: str,
    description: str
):
    """Log a change in visibility/suppression."""
    if old_level == new_level:
        return

    factors = {
        "previous_visibility": old_level,
        "new_visibility": new_level,
        "trigger_reason": reason_code
    }
    
    summary = f"Visibility updated to {new_level}. Reason: {description}"
    
    _create_trace(
        db,
        cluster_id=cluster_id,
        decision_type=AuditDecisionType.NOISE_SUPPRESSION,
        summary=summary,
        factors=factors
    )


def log_narrative_state_change(
    db: Session,
    narrative_id: uuid.UUID, # We might log this against a primary cluster or just null cluster_id?
    # Schema requires cluster_id. If no cluster is specific, null is checked.
    # The requirement says "decision traces for each cluster". 
    # But narrative changes affect all clusters. 
    # For now, we allow null cluster_id in DB, or we log it generally.
    old_state: str,
    new_state: str,
    velocity_trend: str # "INCREASING", "DECREASING", "STABLE"
):
    """Log a narrative lifecycle transition."""
    if old_state == new_state:
        return

    factors = {
        "previous_state": old_state,
        "new_state": new_state,
        "activity_trend": velocity_trend
    }
    
    summary = f"Narrative lifecycle transitioned from {old_state} to {new_state} due to {velocity_trend.lower()} mention velocity."
    
    # We pass None for cluster_id as this is a narrative-level event
    _create_trace(
        db,
        cluster_id=None, 
        decision_type=AuditDecisionType.NARRATIVE_STATE,
        summary=summary,
        factors=factors
    )


def log_editorial_decision(
    db: Session,
    cluster_id: uuid.UUID,
    action: str,
    reviewer_id: str,
    reason: str
):
    """Log a human intervention."""
    factors = {
        "reviewer_action": action,
        "reviewer_id_hash": str(hash(reviewer_id))[:8], # Partial obscuration for public transparency? Or full ID? 
                                                        # "Transparency exists to build trust". 
                                                        # Internal audit needs full ID. We store full in EditorReview table. 
                                                        # Here in factors we can just say "HUMAN_REVIEWER".
        "trigger_context": reason
    }
    
    summary = f"Editorial review completed with action: {action}."
    
    _create_trace(
        db,
        cluster_id=cluster_id,
        decision_type=AuditDecisionType.EDITORIAL_REVIEW,
        summary=summary,
        factors=factors
    )


def _create_trace(
    db: Session,
    cluster_id: Optional[uuid.UUID],
    decision_type: AuditDecisionType,
    summary: str,
    factors: Dict
):
    trace = AuditTrace(
        cluster_id=cluster_id,
        decision_type=decision_type,
        decision_summary=summary,
        factors=factors
    )
    db.add(trace)
    # Don't commit here, usually part of larger transaction


def _qualify_metrics(metrics: Dict[str, Any]) -> Dict[str, str]:
    """Transform raw numbers into qualitative signals."""
    # E.g. source_count -> "SINGLE" | "MULTIPLE" | "BROAD"
    # trust_score -> "LOW" | "MEDIUM" | "HIGH"
    
    q = {}
    
    sc = metrics.get('unique_sources_count', 0)
    if sc <= 1:
        q['source_breadth'] = "SINGLE_SOURCE"
    elif sc < 5:
        q['source_breadth'] = "LIMITED"
    else:
        q['source_breadth'] = "BROAD"
        
    # We assume metrics dict has 'avg_trust' or similar if relevant
    # If not, we skip.
    
    return q
