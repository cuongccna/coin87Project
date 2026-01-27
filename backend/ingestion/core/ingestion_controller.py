"""
Ingestion Controller for Coin87.

COIN87 MANIFESTO LOCK:
"On Information, Trust, and Silence"

This module enforces the Integration Workflow.
It is the centralized authority that orchestrates the:
1. FetchScheduler (Timeline)
2. HealthMonitor (Condition)
3. CircuitBreaker (Permission)
4. NetworkClient (Execution)

NO fetch occurs unless strictly authorized.
"""

from __future__ import annotations

import logging
from typing import Optional
import httpx

from ingestion.core.network_client import NetworkClient
from ingestion.core.behavior import FetchScheduler
from ingestion.core.circuit_breaker import CircuitState
from ingestion.core.health import HealthStatus

logger = logging.getLogger(__name__)

class IngestionController:
    """
    Orchestration layer for secure ingestion.
    Prevents bypassing of safety controls.
    """
    
    def __init__(self, network_client: NetworkClient, scheduler: FetchScheduler):
        self.client = network_client
        self.scheduler = scheduler
        # Dependencies extracted from client for unified state
        self.health_monitor = network_client._health_monitor
        self.circuit_breaker = network_client._circuit_breaker

    async def ingest_source(self, source_id: str, url: str) -> bool:
        """
        Attempt to ingest from a source, adhering to strict safety protocols.
        
        Flow:
        1. Scheduler Check -> Is it time?
        2. Health Check -> Is source healthy?
        3. Circuit Check -> Is breaker closed?
        4. Execution -> Fetch
        
        Returns:
            bool: True if fetch was attempted (success or handled failure), 
                  False if skipped/silenced.
        """
        state = self.client._get_or_create_state(source_id)

        # ---------------------------------------------------------
        # 1. FetchScheduler: TIMELINE AUTHORITY
        # ---------------------------------------------------------
        if not self.scheduler.should_fetch_now(state):
            # Silent skip. No logs.
            return False

        # ---------------------------------------------------------
        # 2. HealthMonitor: CONDITION AUTHORITY
        # ---------------------------------------------------------
        # Note: NetworkClient creates the health object on demand, ensure it exists
        health_obj = self.client._get_health_object(source_id)
        current_status = health_obj.status()
        
        # ALLOW: HEALTHY, DEGRADED
        # BLOCK: UNHEALTHY
        if current_status == HealthStatus.UNHEALTHY:
            # Check for rare "probe" overrides or just enforce silence?
            # Manifesto says: "Prevents NetworkClient from hitting unhealthy sources"
            # Unhealthy sources should be cooling down via Scheduler/Circuit anyway.
            # But this is an explicit guard.
            return False

        # ---------------------------------------------------------
        # 3. CircuitBreaker: GATING AUTHORITY
        # ---------------------------------------------------------
        if not self.circuit_breaker.can_fetch(source_id):
            # Circuit is OPEN.
            return False
            
        # ---------------------------------------------------------
        # 4. Half-Open / Probe Logic
        # ---------------------------------------------------------
        cb_state = self.circuit_breaker.current_state(source_id)
        is_probe = (cb_state == CircuitState.HALF_OPEN)
        
        if is_probe:
             logger.info(f"PROBE attempt for {source_id} (Half-Open)")

        # ---------------------------------------------------------
        # 5. NetworkClient: EXECUTION
        # ---------------------------------------------------------
        # We assume NetworkClient handles the recording of results via internal
        # integration with HM/CB (which we verified in previous step).
        try:
            response = await self.client.fetch(url, source_id, is_probe=is_probe)
            return response is not None
        except Exception as e:
            logger.exception(f"Unexpected error in ingestion flow for {source_id}")
            return False
            
    def get_diagnostics(self, source_id: str) -> dict:
        """
        Internal observability. strictly read-only.
        """
        state = self.client._get_or_create_state(source_id)
        health = self.client._get_health_object(source_id)
        
        return {
            "source_id": source_id,
            "can_fetch_scheduler": self.scheduler.should_fetch_now(state),
            "health_score": health.health_score,
            "health_status": health.status(),
            "circuit_state": self.circuit_breaker.current_state(source_id),
            "next_schedule": self.scheduler.next_fetch_at(state).isoformat() if self.scheduler.next_fetch_at(state) else None
        }
