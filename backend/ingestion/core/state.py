"""
Core state models for Coin87 Network Client.

Separated to avoid circular dependencies between NetworkClient and Scheduling logic.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict

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
    
    # Scheduling
    last_fetch_at: Optional[datetime] = None
    avg_interval: float = AVG_INTERVAL_DEFAULT
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
