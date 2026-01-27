"""
Circuit Breaker for Coin87.

COIN87 MANIFESTO LOCK:
"On Information, Trust, and Silence"

The Circuit Breaker is the ultimate authority on whether a fetch occurs.
It protects the ecosystem from aggressive retries and ensures that
unhealthy sources are given ample time to recover (or be forgotten).

States:
- CLOSED: Normal operation.
- OPEN: Source is unavailable. No requests allowed.
- HALF_OPEN: Probing state. Limited requests allowed to test recovery.

"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

# Import HealthStatus for signal integration
from ingestion.core.health import HealthStatus

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Blocked / Cooling down
    HALF_OPEN = "half_open" # Probing


class SourceCircuitState(BaseModel):
    """
    Persistent state for a source's circuit breaker.
    """
    source_id: str
    state: CircuitState = CircuitState.CLOSED
    
    # Tracking Open Cycles for exponential backoff
    open_cycle_count: int = 0
    
    # Timing
    last_state_change: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cooldown_until: Optional[datetime] = None
    
    model_config = ConfigDict(frozen=False)


class CircuitBreaker:
    """
    Gatekeeper logic for network interactions.
    """
    
    def __init__(self, state_store: Dict[str, SourceCircuitState] = None):
        self._states: Dict[str, SourceCircuitState] = state_store if state_store is not None else {}

    def can_fetch(self, source_id: str) -> bool:
        """
        Determines if a fetch is allowed for this source.
        
        Logic:
        - CLOSED: Yes.
        - OPEN: No, unless cooldown has expired (triggers transition to HALF_OPEN).
        - HALF_OPEN: Yes (Single Probe).
        """
        state = self._get_or_create_state(source_id)
        now = datetime.now(timezone.utc)

        if state.state == CircuitState.CLOSED:
            return True

        if state.state == CircuitState.OPEN:
            # Check cooldown
            if state.cooldown_until and now >= state.cooldown_until:
                # Cooldown expired. Transition to HALF_OPEN for a probe.
                self._transition(state, CircuitState.HALF_OPEN, "Cooldown expired. Probing.")
                return True
            return False

        if state.state == CircuitState.HALF_OPEN:
            # We are in probing mode.
            # In a distributed system, we might need a lock here to prevent parallel probes.
            # For this implementations, we assume the caller respects the single-threaded/locked nature of the runner.
            return True

        return False

    def handle_health_signal(self, source_id: str, new_health_status: HealthStatus):
        """
        Main input vector for state changes based on HealthMonitor.
        
        Call this AFTER updating the HealthMonitor.
        """
        state = self._get_or_create_state(source_id)
        
        # If we are CLOSED but health drops to UNHEALTHY -> Trip Circuit
        if state.state == CircuitState.CLOSED:
            if new_health_status == HealthStatus.UNHEALTHY:
                self._trip_circuit(state, "Health dropped to UNHEALTHY")
                
        # (HALF_OPEN logic is handled in record_probe_result usually)

    def record_probe_result(self, source_id: str, success: bool):
        """
        Handle the result of a fetch attempt while in HALF_OPEN state.
        
        - Success: Reset to CLOSED.
        - Failure: Trip back to OPEN (and increase backoff).
        """
        state = self._get_or_create_state(source_id)
        
        # Only relevant if we are actually probing or potentially effectively probing
        if state.state == CircuitState.HALF_OPEN:
            if success:
                self._reset_circuit(state)
            else:
                self._trip_circuit(state, "Probe failed")
                
        # Edge case: If we were CLOSED but failed catastrophically? 
        # Usually handle_health_signal takes care of that loop.

    def _get_or_create_state(self, source_id: str) -> SourceCircuitState:
        if source_id not in self._states:
            self._states[source_id] = SourceCircuitState(source_id=source_id)
        return self._states[source_id]

    def _transition(self, state: SourceCircuitState, new_state: CircuitState, reason: str):
        """Execute explicit state transition."""
        if state.state != new_state:
            old_state = state.state
            state.state = new_state
            state.last_state_change = datetime.now(timezone.utc)
            logger.info(f"Circuit {state.source_id}: {old_state} -> {new_state} | {reason}")

    def _trip_circuit(self, state: SourceCircuitState, reason: str):
        """
        Move to OPEN state and calculate cooldown.
        Escalates backoff based on how many times we've been here.
        """
        # Increment cycle count
        state.open_cycle_count += 1
        
        # Calculate Cooldown
        # 1st time: 1 hour
        # 2nd time: 6 hours
        # 3rd time: 24 hours
        # 4th+ time: 48 hours
        
        hours = 1
        if state.open_cycle_count == 2:
            hours = 6
        elif state.open_cycle_count == 3:
            hours = 24
        elif state.open_cycle_count >= 4:
            hours = 48
            
        cooldown_duration = timedelta(hours=hours)
        state.cooldown_until = datetime.now(timezone.utc) + cooldown_duration
        
        self._transition(state, CircuitState.OPEN, f"{reason}. Backoff: {hours}h (Cycle {state.open_cycle_count})")

    def _reset_circuit(self, state: SourceCircuitState):
        """
        Move to CLOSED state.
        Optionally reset cycle count or decay it.
        Manifesto: "Recover slowly". We might not reset open_cycle_count immediately to 0?
        For now, we reset state to CLOSED, but keep cycle_count high? 
        No, usually successful probe means we are good. We'll reset cycle_count to give them a fresh chance,
        relying on HealthMonitor to degrade fast if they fail again.
        """
        state.open_cycle_count = 0 
        state.cooldown_until = None
        self._transition(state, CircuitState.CLOSED, "Probe succeeded. Circuit closed.")

    def current_state(self, source_id: str) -> CircuitState:
        return self._get_or_create_state(source_id).state

    def next_retry_at(self, source_id: str) -> Optional[datetime]:
        state = self._get_or_create_state(source_id)
        return state.cooldown_until
