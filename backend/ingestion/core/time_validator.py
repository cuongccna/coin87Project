"""
Timeline Consistency Validator for Coin87.

COIN87 MANIFESTO LOCK:
"On Information, Trust, and Silence"

Time inconsistencies are not just data errors; they are narrative corruptions.
This module guards the timeline against:
- Future timestamps (Time Travel)
- Backward jumps (History Rewrite)
- Stale inferences pretending to be current
- Source clock drift

We DO NOT silently fix time. We flag it.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import List, Optional, Protocol, Tuple

from pydantic import BaseModel, ConfigDict, Field

from ingestion.core.time_common import TimeRecord, TimeConfidence, TimeFormat
from ingestion.core.state import SourceState

logger = logging.getLogger(__name__)


class AnomalyType(str, Enum):
    FUTURE_TIMESTAMP = "future_timestamp"
    BACKWARD_JUMP = "backward_jump"
    TIME_REVERSAL_PATTERN = "time_reversal_pattern"
    STALE_RELATIVE_INFERENCE = "stale_relative_inference"
    SOURCE_CLOCK_DRIFT = "source_clock_drift"
    INCEPTION_VIOLATION = "inception_violation"
    CLUSTER_BOUNDS_ERROR = "cluster_bounds_error"
    LIFECYCLE_REGRESSION = "lifecycle_regression"


class ValidationStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


class ValidationAction(str, Enum):
    IGNORE = "ignore"
    FLAG = "flag"           # Mark record/source but process
    QUARANTINE = "quarantine" # Do not process further
    DOWNGRADE = "downgrade" # Reduce confidence


class ValidationResult(BaseModel):
    """
    Outcome of a consistency check.
    Must be stored alongside the item for auditability.
    """
    status: ValidationStatus
    anomaly_type: Optional[AnomalyType] = None
    message: str = "Validation passed"
    affected_scope: str # item, source, cluster, narrative
    recommended_action: ValidationAction = ValidationAction.IGNORE
    
    model_config = ConfigDict(frozen=True)


class TimelineConsistencyValidator:
    """
    The Guardian of Chronology.
    """
    
    # Tolerance for "Future" timestamps (allow slight clock skew from servers)
    FUTURE_TOLERANCE = timedelta(minutes=5)
    
    # If a relative time (like "2 years ago") is used, we flag it if > 30 days
    # because resolving "3 years ago" to a specific second is misleadingly precise.
    STALE_INFERENCE_THRESHOLD = timedelta(days=30)

    def validate_item(
        self, 
        record: TimeRecord, 
        source_state: Optional[SourceState] = None,
        fetch_time: Optional[datetime] = None
    ) -> ValidationResult:
        """
        Validate a single TimeRecord against physical constraints.
        
        Checks:
        - Absolute future (UTC now + tolerance)
        - Stale relative inferences
        """
        now = fetch_time or datetime.now(timezone.utc)
        
        # 1. Check Future Timestamp
        # Data claiming to be from the future is a critical reliability risk.
        if record.utc_timestamp > (now + self.FUTURE_TOLERANCE):
            time_diff = record.utc_timestamp - now
            return ValidationResult(
                status=ValidationStatus.ERROR,
                anomaly_type=AnomalyType.FUTURE_TIMESTAMP,
                message=f"Item is {time_diff} in the future",
                affected_scope="item",
                recommended_action=ValidationAction.QUARANTINE
            )
            
        # 2. Check Stale Relative Inference
        # If we inferred "3 months ago", that's a very low confidence guess.
        # It shouldn't be treated as a precise fact.
        if record.parsed_format == TimeFormat.RELATIVE and record.reference_time:
            delta = record.reference_time - record.utc_timestamp
            if delta > self.STALE_INFERENCE_THRESHOLD:
                return ValidationResult(
                    status=ValidationStatus.WARNING,
                    anomaly_type=AnomalyType.STALE_RELATIVE_INFERENCE,
                    message=f"Relative inference is stale ({delta.days} days old)",
                    affected_scope="item",
                    recommended_action=ValidationAction.FLAG
                )

        # 3. Source Inception (if known)
        # Cannot publish before source existed.
        # (Requires inception_date on SourceState, stubbed here logic-wise)
        # if source_state and source_state.inception_at and record.utc_timestamp < source_state.inception_at:
        #    return ERROR...

        return ValidationResult(
            status=ValidationStatus.OK, 
            affected_scope="item",
            message="Item timestamp is physically valid"
        )

    def validate_source_consistency(
        self, 
        source_id: str, 
        new_record: TimeRecord, 
        previous_records: List[TimeRecord]
    ) -> ValidationResult:
        """
        Validate compatibility with recent history from the SAME source.
        
        Checks:
        - Time Reversal: Are we seeing a stream of items going backwards?
                         (Common in "scrolling down" ingestion, but if "latest" feed goes backwards, it's clock drift or deletion)
        """
        if not previous_records:
            return ValidationResult(status=ValidationStatus.OK, affected_scope="source", message="No history")

        # Sort previous records desc by utc_timestamp
        latest_prev = max(previous_records, key=lambda r: r.utc_timestamp)
        
        # Check for significant backward jump (e.g. > 1 year) which implies bad parsing or source reset
        # Small backward jumps might be out-of-order delivery (acceptable in distributed systems)
        BACKWARD_JUMP_LIMIT = timedelta(days=365)
        
        if latest_prev.utc_timestamp - new_record.utc_timestamp > BACKWARD_JUMP_LIMIT:
             return ValidationResult(
                status=ValidationStatus.WARNING,
                anomaly_type=AnomalyType.BACKWARD_JUMP,
                message=f"Significant backward jump detected (> 1 year) vs latest source item",
                affected_scope="source",
                recommended_action=ValidationAction.FLAG
            )
            
        return ValidationResult(status=ValidationStatus.OK, affected_scope="source", message="Source consistent")

    def validate_cluster(
        self, 
        cluster_id: str, 
        first_seen: datetime, 
        last_seen: datetime
    ) -> ValidationResult:
        """
        Validate logical bounds of a cluster.
        """
        if first_seen > last_seen:
             return ValidationResult(
                status=ValidationStatus.ERROR,
                anomaly_type=AnomalyType.CLUSTER_BOUNDS_ERROR,
                message=f"Cluster {cluster_id} is reversed: first_seen > last_seen",
                affected_scope="cluster",
                recommended_action=ValidationAction.QUARANTINE
            )
            
        return ValidationResult(status=ValidationStatus.OK, affected_scope="cluster", message="Cluster Valid")

    def validate_narrative_lifecycle(
        self,
        narrative_id: str,
        current_stage: str,
        proposed_stage: str
    ) -> ValidationResult:
        """
        Ensures narrative stages move forward (or valid loops), not regression.
        Example: Cannot go from 'Archived' -> 'Emerging' without special handling.
        """
        # Define forbidden transitions (Simplistic example)
        FORBIDDEN = {
            ("archived", "emerging"),
            ("established", "emerging")
        }
        
        if (current_stage, proposed_stage) in FORBIDDEN:
             return ValidationResult(
                status=ValidationStatus.ERROR,
                anomaly_type=AnomalyType.LIFECYCLE_REGRESSION,
                message=f"Invalid narrative transition: {current_stage} -> {proposed_stage}",
                affected_scope="narrative",
                recommended_action=ValidationAction.IGNORE # Reject the update
            )
            
        return ValidationResult(status=ValidationStatus.OK, affected_scope="narrative", message="Lifecycle Valid")
