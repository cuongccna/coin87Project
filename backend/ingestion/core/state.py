"""
Core state models for Coin87 Network Client.

Separated to avoid circular dependencies between NetworkClient and Scheduling logic.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.db import SessionLocal
from app.models.source_health import SourceHealth

# Shared Constants
MIN_INTERVAL_SECONDS = 5.0
AVG_INTERVAL_DEFAULT = 30.0
JITTER_FACTOR = 0.4
SOFT_BLOCK_COOLDOWN_MINUTES = 15
HARD_BLOCK_COOLDOWN_HOURS = 24

class FetchOutcome(str, Enum):
    """Result of a fetch attempt, used for state updates."""
    SUCCESS = "success"
    SOFT_BLOCK = "soft_block"      # Temporary restriction (429, CAPTCHA)
    HARD_BLOCK = "hard_block"      # Persistent restriction (IP ban, 403 permanent)
    TRANSIENT_ERROR = "transient"  # Network glitch, 5xx, timeout


class RequestConfig(BaseModel):
    """Configuration for a single request, representing an 'Identity'."""
    headers: Dict[str, str]
    proxy: Optional[str] = None
    timeout: float = 30.0
    verify_ssl: bool = True
    
    model_config = ConfigDict(frozen=True)


class SourceState(BaseModel):
    """
    Mutable state for a specific data source.
    
    Maintains the health, identity, and scheduling parameters for a source.
    This state must be persisted between sessions to ensure continuity.
    """
    source_id: str
    
    # Scheduling & Health
    status: str = "HEALTHY"  # HEALTHY, DEGRADED, OPEN
    failure_count: int = 0
    next_allowed_at: Optional[datetime] = None
    
    # Conditional Fetch
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    
    # Operational
    last_fetch_at: Optional[datetime] = None
    avg_interval: float = AVG_INTERVAL_DEFAULT
    
    def can_fetch(self) -> bool:
        if self.next_allowed_at and datetime.now(timezone.utc) < self.next_allowed_at:
            return False
        if self.status == "OPEN":
            # Check if cooldown passed (redundant with next_allowed_at but safe)
            pass
        return True


class PostgresStateStore:
    """Persists operational state to PostgreSQL source_health_states table."""
    
    def load_state(self, source_id: str) -> SourceState:
        with SessionLocal() as session:
            record = session.query(SourceHealth).filter(SourceHealth.source_id == source_id).first()
            
            if not record:
                # Return default minimal state
                return SourceState(source_id=source_id)
            
            # Ensure timezone awareness
            next_allowed = record.next_allowed_at
            if next_allowed and next_allowed.tzinfo is None:
                next_allowed = next_allowed.replace(tzinfo=timezone.utc)
                
            last_run = record.last_run_at
            if last_run and last_run.tzinfo is None:
                last_run = last_run.replace(tzinfo=timezone.utc)

            return SourceState(
                source_id=source_id,
                status=record.status,
                failure_count=record.failure_count,
                next_allowed_at=next_allowed,
                etag=record.etag,
                last_modified=record.last_modified,
                last_fetch_at=last_run
            )

    def update_state(self, source_id: str, outcome: FetchOutcome, next_run: Optional[datetime] = None, etag: str = None, last_modified: str = None):
        """Updates state transactionally."""
        
        # Calculate new status logic
        status_update = {}
        now = datetime.now(timezone.utc)
        
        status_update["last_run_at"] = now
        
        if etag:
            status_update["etag"] = etag
        if last_modified:
            status_update["last_modified"] = last_modified
            
        if outcome == FetchOutcome.SUCCESS:
            status_update["status"] = "HEALTHY"
            status_update["failure_count"] = 0
            status_update["last_success_at"] = now
            status_update["next_allowed_at"] = next_run # Respect the random jitter calculated by caller
            
        elif outcome == FetchOutcome.SOFT_BLOCK:
            status_update["status"] = "DEGRADED"
            # failure_count incremented in SQL below or we can fetch-modify-save. 
            # Simplified: Let's assume caller logic handles the next_allowed_at duration.
             # But failure_count logic is better handled here or we read-modify-write.
            status_update["next_allowed_at"] = now + timedelta(minutes=SOFT_BLOCK_COOLDOWN_MINUTES)
            
        elif outcome == FetchOutcome.HARD_BLOCK:
            status_update["status"] = "OPEN"
            status_update["next_allowed_at"] = now + timedelta(hours=HARD_BLOCK_COOLDOWN_HOURS)
        
        elif outcome == FetchOutcome.TRANSIENT_ERROR:
             # Just update valid-time, don't change status immediately unless threshold logic is here.
             # We rely on existing CircuitBreaker logic to decide 'status', 
             # but here we just persist what we're told or minimal updates.
             pass

        # If the caller provided a specific next_run (e.g. from rate limiter), respect it if it extends the block
        if next_run:
             # Basic logic: take the max of enforced cooldown vs requested schedule
             current_unblock = status_update.get("next_allowed_at")
             if not current_unblock or next_run > current_unblock:
                 status_update["next_allowed_at"] = next_run
        
        with SessionLocal() as session:
             # We use the ORM for logic simplicity over raw perf
             record = session.query(SourceHealth).filter(SourceHealth.source_id == source_id).first()
             if not record:
                 record = SourceHealth(source_id=source_id, failure_count=0, status="HEALTHY")
                 session.add(record)
            
             # Apply updates
             for k, v in status_update.items():
                 setattr(record, k, v)
                 
             if outcome != FetchOutcome.SUCCESS:
                 if record.failure_count is None:
                     record.failure_count = 0
                 record.failure_count += 1
                 if record.failure_count >= 5 and record.status != "OPEN":
                     record.status = "OPEN"
                     # Force 24h cooldown if we hit the limit
                     record.next_allowed_at = now + timedelta(hours=24)
             else:
                 record.failure_count = 0
            
             session.commit()
    cooldown_until: Optional[datetime] = None
    
    # State & Health
    health_score: float = 1.0  # 0.0 to 1.0
    soft_block_count: int = 0
    hard_block_count: int = 0
    
    # Identity (Sticky Session)
    # The ID of the IdentityProfile currently assigned to this source.
    # The actual profile data is managed by ProfileManager.
    assigned_profile_id: Optional[str] = None
    
    model_config = ConfigDict(validate_assignment=True)

    def is_cooling_down(self) -> bool:
        """Check if source is currently in a penalty cooldown."""
        if self.cooldown_until and datetime.now(timezone.utc) < self.cooldown_until:
            return True
        return False
