"""
Health Monitor for Coin87.

COIN87 MANIFESTO LOCK:
"On Information, Trust, and Silence"

This module acts as the immune system for the ingestion layer.
It observes source behavior and acts as the authority on whether a source is fit for interaction.

Principles:
- Failures have momentum: A source that fails is likely to fail again.
- Trust is earned slowly: Recovery is gradual, not instantaneous.
- Silence is a valid response: If a source is unhealthy, we step back.
"""

from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Deque, Optional

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """
    Categorical status of a source derived from its continuous health score.
    """
    HEALTHY = "healthy"         # Score > 0.8. Nominal operation.
    DEGRADED = "degraded"       # Score 0.4 - 0.8. Reduced frequency, heightened monitoring.
    UNHEALTHY = "unhealthy"     # Score < 0.4. Quarantine or very long backoff.


class ErrorType(str, Enum):
    """
    Classification of failures for weighted scoring.
    """
    NETWORK_TIMEOUT = "network_timeout"      # Transients
    HTTP_5XX = "http_5xx"                    # Server side issues
    HTTP_4XX = "http_4xx"                    # Client side / Permissions
    SOFT_BLOCK = "soft_block"                # Rate limits, Captchas (Serious)
    HARD_BLOCK = "hard_block"                # IP Bans, Access Denied (Critical)
    CONTENT_EMPTY = "content_empty"          # Payload validity
    TIME_ANOMALY = "time_anomaly"            # Timekeeper signals
    PARSE_ERROR = "parse_error"              # Schema mismatch


class SourceHealth(BaseModel):
    """
    Persistent health state for a single source.
    Verified and updated by the HealthMonitor.
    """
    source_id: str
    
    # Core Score
    health_score: float = Field(default=1.0, ge=0.0, le=1.0)
    
    # Streaks & Stats
    error_streak: int = 0
    success_streak: int = 0
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    
    # Windowed Metrics
    # We keep the last N error types to detect repetitive patterns
    recent_errors: Deque[ErrorType] = Field(default_factory=lambda: deque(maxlen=10))
    avg_response_time: float = 0.0  # Moving average in seconds
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def status(self) -> HealthStatus:
        """Derive categorical status from score."""
        if self.health_score > 0.8:
            return HealthStatus.HEALTHY
        elif self.health_score > 0.4:
            return HealthStatus.DEGRADED
        return HealthStatus.UNHEALTHY


class HealthMonitor:
    """
    Evaluates and updates source health based on interaction outcomes.
    
    Enforces the "Slow Recovery, Fast Degradation" specific logic.
    """
    
    # --- Scoring Weights ---
    # Penalties are subtracted from health_score [0, 1]
    PENALTY_MAP = {
        ErrorType.NETWORK_TIMEOUT: 0.1,    # Annoying, but maybe transient
        ErrorType.HTTP_5XX: 0.15,          # Server struggling
        ErrorType.HTTP_4XX: 0.2,           # Configuration or permission error
        ErrorType.SOFT_BLOCK: 0.3,         # We are being annoying. Back off hard.
        ErrorType.HARD_BLOCK: 1.0,         # Game over.
        ErrorType.CONTENT_EMPTY: 0.1,      # Glitch
        ErrorType.TIME_ANOMALY: 0.25,      # Trust issue. Serious.
        ErrorType.PARSE_ERROR: 0.05,       # Maybe layout change, less critical for trust
    }
    
    # Recovery
    RECOVERY_INCREMENT = 0.05       # Flat bonus for a success
    MAX_RECOVERY_PER_HOUR = 0.2     # Cap to prevent "flapping"
    
    def record_success(self, health: SourceHealth, latency_seconds: float) -> SourceHealth:
        """
        Register a successful interaction.
        
        Effect:
        - Resets error streak.
        - Increments success streak.
        - Slowly recovers health score.
        - Updates moving average latency.
        """
        now = datetime.now(timezone.utc)
        
        # 1. Update Streaks
        health.error_streak = 0
        health.success_streak += 1
        health.last_success_at = now
        
        # 2. Update Latency (Exponential Moving Average)
        # Alpha 0.2 means recent values weigh 20%
        if health.avg_response_time == 0:
            health.avg_response_time = latency_seconds
        else:
            health.avg_response_time = (health.avg_response_time * 0.8) + (latency_seconds * 0.2)
            
        # 3. Latency Penalty check
        # If latency is abnormally high, we don't reward as much, or trigger a degradation.
        # Simple heuristic: > 10s is unhealthy for human browsing simulation.
        latency_penalty = 0.0
        if latency_seconds > 10.0:
            latency_penalty = 0.05
            logger.debug(f"Source {health.source_id} slow response ({latency_seconds:.2f}s). Penalty applied.")

        # 4. Calculate Recovery
        # "Trust is earned slowly."
        # We limit how much health can be regained in short bursts.
        # (This simple implementation just adds strict increments).
        
        raw_gain = self.RECOVERY_INCREMENT - latency_penalty
        new_score = health.health_score + max(0.0, raw_gain)
        
        # Cap at 1.0
        health.health_score = min(1.0, new_score)
        
        return health

    def record_failure(self, health: SourceHealth, error_type: ErrorType) -> SourceHealth:
        """
        Register a failed interaction.
        
        Effect:
        - Resets success streak.
        - Increments error streak.
        - Applies significant health penalty.
        - Tracks error type for pattern recognition.
        """
        now = datetime.now(timezone.utc)
        
        # 1. Update Streaks
        health.success_streak = 0
        health.error_streak += 1
        health.last_failure_at = now
        health.recent_errors.append(error_type)
        
        # 2. Calculate Base Penalty
        base_penalty = self.PENALTY_MAP.get(error_type, 0.1)
        
        # 3. Apply Multipliers for Persistence
        # "Failures have momentum."
        # If we see the SAME error repeatedly, the penalty escalates.
        if health.error_streak > 1 and list(health.recent_errors)[-2] == error_type:
            multiplier = 1.0 + (0.5 * min(health.error_streak, 4)) # 1.5x, 2.0x, 2.5x...
            penalty = base_penalty * multiplier
            logger.info(f"Escalating penalty for {health.source_id} (Streak {health.error_streak} x {error_type})")
        else:
            penalty = base_penalty
            
        # 4. Apply Penalty
        health.health_score = max(0.0, health.health_score - penalty)
        
        logger.warning(
            f"Source {health.source_id} Health Drop: "
            f"-{penalty:.2f} -> {health.health_score:.2f} [{error_type}]"
        )
        
        return health

    def evaluate_health(self, health: SourceHealth) -> HealthStatus:
        """
        Categorize the continuous score into a decision status.
        Used by the Scheduler / Circuit Breaker.
        """
        return health.status()
