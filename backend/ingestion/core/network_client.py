"""
NetworkClient for Coin87.

COIN87 MANIFESTO LOCK:
"On Information, Trust, and Silence"

This client is designed to:
- Simulate calm, human-like browsing.
- Prioritize durability and stealth over speed.
- adhere strictly to non-aggressive crawling policies.

Design Principles:
- Deterministic logic where possible.
- Explicit state management.
- Graceful degradation in face of resistance.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Protocol

import httpx

from ingestion.core.state import (
    AVG_INTERVAL_DEFAULT,
    HARD_BLOCK_COOLDOWN_HOURS,
    JITTER_FACTOR,
    MIN_INTERVAL_SECONDS,
    SOFT_BLOCK_COOLDOWN_MINUTES,
    FetchOutcome,
    RequestConfig,
    SourceState,
)
from ingestion.core.identity import ProfileManager, IdentityProfile
from ingestion.core.health import HealthMonitor, ErrorType, HealthStatus
from ingestion.core.circuit_breaker import CircuitBreaker, CircuitState

# Configure logging to be minimal but informative
logger = logging.getLogger(__name__)

# Constants for timing and behavior (Human-like parameters)
MAX_RETRIES = 2  # Low retry count to avoid aggression


class NetworkClient:
    """
    Core HTTP Client for Coin87.
    
    The ONLY gateway for external requests.
    Enforces manifesto constraints: calm, sustainable, human-like.
    """

    def __init__(
        self, 
        state_store: Dict[str, SourceState] = None, 
        profile_manager: ProfileManager = None,
        health_monitor: HealthMonitor = None,
        circuit_breaker: CircuitBreaker = None
    ):
        """
        Initialize the NetworkClient.
        
        Args:
           state_store: Optional dictionary to persist state in-memory. 
                        In production, this should interface with a DB.
           profile_manager: Optional manager for browser identities.
           health_monitor: Optional manager for source health scoring.
           circuit_breaker: Optional gatekeeper logic.
        """
        self._states: Dict[str, SourceState] = state_store if state_store is not None else {}
        self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        self._profile_manager = profile_manager or ProfileManager()
        self._health_monitor = health_monitor or HealthMonitor()
        self._circuit_breaker = circuit_breaker or CircuitBreaker()
        
        # In-memory mapping to map SourceState IDs to Health objects
        self._health_states = {}

    async def fetch(self, url: str, source_id: str, is_probe: bool = False) -> Optional[httpx.Response]:
        """
        Execute a managed fetch request to the target URL.
        
        Orchestrates:
        1. Circuit Breaker Check
        2. Scheduling check (is it too soon?)
        3. Identity application (headers/proxy)
        4. Execution
        5. Analysis
        6. State update (Health + Circuit)
        
        Args:
            url: Target URL.
            source_id: Unique source identifier.
            is_probe: If True, this is a distinct health probe (Half-Open state).

        Returns:
            httpx.Response object if allowed and successful, None if blocked/skipped.
        """
        state = self._get_or_create_state(source_id)
        
        # 1. Circuit Breaker Check
        # The Circuit Breaker has authority over crawling.
        # Defense in depth: IngestionController should have checked this, 
        # but NetworkClient refuses to operate against an OPEN circuit.
        if not self._circuit_breaker.can_fetch(source_id):
            next_retry = self._circuit_breaker.next_retry_at(source_id)
            logger.warning(f"BLOCKED {source_id}: Circuit OPEN. Retry at {next_retry}")
            return None

        # 2. Check Scheduling Constraints
        # In PROBE mode, we might override minor timing issues, but generally strict.
        if not is_probe and state.is_cooling_down():
            logger.info(f"Skipping {source_id}: In cooldown until {state.cooldown_until}")
            return None
            
        next_allowed = self.schedule_next(source_id)
        # Only allow fetch if enough time has passed since last_fetch_at
        if not is_probe and state.last_fetch_at and next_allowed > datetime.now(timezone.utc):
            wait_time = (next_allowed - datetime.now(timezone.utc)).total_seconds()
            if wait_time > 1: # Tolerance for small drifts
                logger.info(f"Skipping {source_id}: Too soon. Next allowed: {next_allowed}")
                return None

        # 3. Apply Identity
        # WHY: To mimic a consistent human browser session.
        config = self.apply_identity(source_id)
        
        if is_probe:
            logger.info(f"Executing PROBE fetch for {source_id}...")
        else:
            logger.debug(f"Fetching {url} for {source_id}...")
        
        start_time = datetime.now(timezone.utc)
        response = None
        
        try:
            # 4. Network Execution
            # In Half-Open state, we might restrict this further (e.g. HEAD only)
            response = await self._client.get(
                url, 
                headers=config.headers, 
                proxies=config.proxy
            )
            
            # 5. Response Evaluation
            outcome = self.analyze_response(response)
            
        except httpx.RequestError as e:
            logger.warning(f"Network error for {source_id}: {str(e)}")
            outcome = FetchOutcome.TRANSIENT_ERROR
            
        latency = (datetime.now(timezone.utc) - start_time).total_seconds()

        # 6. Update State
        self.update_source_state(source_id, outcome, latency)
        
        # Report block to ProfileManager for identity health tracking
        if outcome in [FetchOutcome.HARD_BLOCK, FetchOutcome.SOFT_BLOCK]:
            self._profile_manager.report_block(
                source_id, 
                is_hard_block=(outcome == FetchOutcome.HARD_BLOCK)
            )

        # Only return response if it was a success or soft/transient failure where content exists
        if outcome == FetchOutcome.HARD_BLOCK:
            return None
            
        return response

    def schedule_next(self, source_id: str) -> datetime:
        """
        Calculate the next permissible fetch time.
        
        Logic:
        - Base: last_fetch_at + avg_interval
        - Jitter: Add random % to interval to avoid machine-like patterns.
        - Backoff: implicitly handled by 'avg_interval' adjustments in update_source_state.
        """
        state = self._get_or_create_state(source_id)
        
        if not state.last_fetch_at:
            return datetime.now(timezone.utc)
        
        # Apply Jitter
        # WHY: Fixed intervals (e.g. exactly every 60s) are a bot fingerprint.
        jitter_range = state.avg_interval * JITTER_FACTOR
        jitter_val = random.uniform(-jitter_range, jitter_range)
        actual_interval = max(MIN_INTERVAL_SECONDS, state.avg_interval + jitter_val)
        
        return state.last_fetch_at + timedelta(seconds=actual_interval)

    def apply_identity(self, source_id: str) -> RequestConfig:
        """
        Construct the request identity (Headers + Proxy + UA).
        
        Uses BehaviorProfileManager to ensure consistency and affinity.
        """
        state = self._get_or_create_state(source_id)
        
        # Delegate to ProfileManager
        profile = self._profile_manager.get_profile_for_source(
            source_id, 
            current_profile_id=state.assigned_profile_id
        )
        
        # Persist the assignment ID back to state
        if state.assigned_profile_id != profile.id:
            state.assigned_profile_id = profile.id
            logger.info(f"Source {source_id} attached to Identity {profile.id}")

        # Construct RequestConfig from IdentityProfile
        proxy_url = profile.proxy_profile.proxy_url if profile.proxy_profile else None
        
        return RequestConfig(headers=profile.headers, proxy=proxy_url)

    def analyze_response(self, response: httpx.Response) -> FetchOutcome:
        """
        Heuristic analysis of the response to detect blocks or issues.
        
        Detects:
        - HTTP Status codes indicating blocks (403, 429).
        - Soft blocks (CAPTCHAs, textual warnings).
        - Content validity (Empty body).
        - Abnormal latency spikes (Tarpitting).
        - JS-required placeholders.
        """
        if response is None:
            return FetchOutcome.TRANSIENT_ERROR

        # 0. Latency Check
        # Abnormal latency (e.g. > 15s) often suggests server-side bandwidth throttling (tar pitting)
        if response.elapsed.total_seconds() > 15.0:
            logger.warning("Abnormal latency detected (>15s). Possible throttling.")
            return FetchOutcome.SOFT_BLOCK

        # 1. HTTP Status Check
        if response.status_code in [403, 406]:
            # Forbidden/Not Acceptable - likely User-Agent or IP block
            return FetchOutcome.HARD_BLOCK
        
        if response.status_code == 429:
            # Too Many Requests - calm down immediately
            return FetchOutcome.SOFT_BLOCK
            
        if response.status_code >= 500:
            return FetchOutcome.TRANSIENT_ERROR
            
        # 2. Content Heuristics
        text = response.text
        
        if not text or len(text) < 100:
             # Empty/Truncated - Suspicious
            return FetchOutcome.TRANSIENT_ERROR

        text_lower = text.lower()

        # JS-Required Placeholders
        # If the content is basically just "Enable JS", we can't read it.
        js_required_markers = [
            "need to enable javascript",
            "javascript is required",
            "enable js to continue",
            "requires javascript"
        ]
        
        if len(text) < 2000: # Usually these are short pages
            for marker in js_required_markers:
                if marker in text_lower:
                    logger.warning("JS-only content detected.")
                    return FetchOutcome.SOFT_BLOCK # Treated as a soft block (content inaccessible)

        # Cloudflare / WAF / Captcha markers
        # WHY: We must not attempt to bypass these. We back off.
        soft_block_markers = [
            "captcha",
            "please verify you are a human",
            "access denied",
            "security check",
            "cloudflare-ray" # Often present on challenge pages
        ]
        
        if response.status_code == 200:
            for marker in soft_block_markers:
                # Naive check - in production refine to avoid false positives in article text
                if marker in text_lower and len(text) < 5000: 
                    # If content is short AND contains markers, it's likely a challenge page
                    return FetchOutcome.SOFT_BLOCK

        return FetchOutcome.SUCCESS

    def update_source_state(self, source_id: str, outcome: FetchOutcome, latency: float = 0.0) -> None:
        """
        Apply consequences of the fetch outcome to the source state.
        
        Delegates complex logic to HealthMonitor and CircuitBreaker.
        """
        state = self._get_or_create_state(source_id)
        now = datetime.now(timezone.utc)
        
        state.last_fetch_at = now
        
        # 1. Map Outcome to Health ErrorType
        # This acts as the bridge between NetworkClient logic and HealthMonitor logic
        if outcome == FetchOutcome.SUCCESS:
            self._handle_health_success(source_id, latency)
        else:
            error_type = self._map_outcome_to_error(outcome)
            self._handle_health_failure(source_id, error_type)
            
        # 2. Sync Back to SourceState
        # The Scheduler uses state.health_score to make decisions.
        # We must update it from the authoritative HealthMonitor.
        health_obj = self._get_health_object(source_id)
        state.health_score = health_obj.health_score

        # 3. Update Circuit Breaker
        # Tell the CB about the new health status so it can trip if needed
        status = health_obj.status()
        self._circuit_breaker.handle_health_signal(source_id, status)
        
        # Handle Half-Open Probe Result
        if self._circuit_breaker.current_state(source_id) == CircuitState.HALF_OPEN:
            success = (outcome == FetchOutcome.SUCCESS)
            self._circuit_breaker.record_probe_result(source_id, success)
            
        # 4. Fallback / Legacy Cooldown Logic
        # (Only if CB doesn't set a harder limit, we might set a soft limit here or remove this)
        # For now, we rely on CB for HARD stops, but SourceState.cooldown_until is still used by Scheduler
        # as a "Soft" cooldown. We should sync them.
        cb_retry = self._circuit_breaker.next_retry_at(source_id)
        if cb_retry:
            state.cooldown_until = cb_retry
        elif outcome == FetchOutcome.SOFT_BLOCK:
             # Keep some local logic for soft blocks if CB didn't trip?
             # Actually, best to just let CB/Health handle it. 
             # But strictly, CB operates on states (Open/Closed). 
             # Soft backoff (minutes) might not trip CB (hours).
             # So we keep the simple backoff here for minor issues.
            pass


    def _handle_health_success(self, source_id: str, latency: float):
        from ingestion.core.health import SourceHealth
        if source_id not in self._health_states:
            self._health_states[source_id] = SourceHealth(source_id=source_id)
            
        self._health_monitor.record_success(self._health_states[source_id], latency)

    def _handle_health_failure(self, source_id: str, error_type: ErrorType):
        from ingestion.core.health import SourceHealth
        if source_id not in self._health_states:
             self._health_states[source_id] = SourceHealth(source_id=source_id)

        self._health_monitor.record_failure(self._health_states[source_id], error_type)

    def _get_health_object(self, source_id: str):
        from ingestion.core.health import SourceHealth
        if source_id not in self._health_states:
             self._health_states[source_id] = SourceHealth(source_id=source_id)
        return self._health_states[source_id]

    def _map_outcome_to_error(self, outcome: FetchOutcome) -> ErrorType:
        if outcome == FetchOutcome.SOFT_BLOCK:
            return ErrorType.SOFT_BLOCK
        if outcome == FetchOutcome.HARD_BLOCK:
            return ErrorType.HARD_BLOCK
        if outcome == FetchOutcome.TRANSIENT_ERROR:
            return ErrorType.NETWORK_TIMEOUT # Generalize
        return ErrorType.HTTP_5XX # Fallback

    def _get_or_create_state(self, source_id: str) -> SourceState:
        """Helper to manage state lifecycle."""
        if source_id not in self._states:
            self._states[source_id] = SourceState(source_id=source_id)
        return self._states[source_id]

    async def close(self):
        """Cleanup resources."""
        await self._client.aclose()
