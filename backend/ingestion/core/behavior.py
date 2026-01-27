"""
Behavior Engine and Fetch Scheduler for Coin87 NetworkClient.

COIN87 MANIFESTO LOCK:
"On Information, Trust, and Silence"

This module controls the 'Rhythm' of the ingestion system.
It enforces silence, delay, and unpredictability to mimic human behavior.

Core Responsibilities:
- Decide WHEN to fetch.
- Decide IF we should skip entirely (simulate distraction/disinterest).
- Calculate "think time" and "long pauses".

EXAMPLE TIMING FLOW (Simulated):
--------------------------------
1. T-00:00 - Fetch Success. Avg Interval: 30m.
   -> BehaviorEngine schedules next check around T+30m +/- 40% jitter.
   -> Calculated: T+24m.

2. T+24:00 - Scheduler wakes up. Source is healthy.
   -> BehaviorEngine rolls 'Skip Probability' (5%). Result: SKIP.
   -> Simulates user getting distracted. Reschedules for T+55m.

3. T+55:00 - Scheduler wakes up.
   -> BehaviorEngine rolls 'Skip' (Failure).
   -> Calculates 'Think Time': 2.3 seconds (simulating mouse movement).
   -> Action: FETCH.
   -> Outcome: SOFT_BLOCK (429).
   -> Source State: Health drops to 0.8. Interval increases to 45m. Cooldown 15m.

4. T+70:00 (15m later) - Cooldown expires.
   -> Scheduler waits for Interval (45m from last attempt).
   -> Next check allowed around T+100m.

Avoids detection by:
- Never hitting the minute mark exactly twice.
- "Forgetting" to check (Skips).
- Ignoring efficiency (Wait times).
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Optional

from ingestion.core.state import (
    SourceState, 
    AVG_INTERVAL_DEFAULT, 
    JITTER_FACTOR, 
    MIN_INTERVAL_SECONDS
)

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class BehaviorProfile:
    """
    Directives for how the client should behave for the immediate next action.
    This is ephemeral; generated fresh at each decision point.
    """
    should_skip: bool
    think_time_delay: float  # Seconds to wait before initiating request
    next_scheduled_fetch: datetime
    reason: str


class BehaviorEngine:
    """
    The Brains. Decides 'How a human would act right now'.
    
    Factors in:
    - Current health of the source (Are they annoyed?)
    - Time of day (Simulated via simple randomness for now)
    - Random "distraction" factors (Humans don't check RSS feeds efficiently)
    """
    
    def generate_profile(self, state: SourceState) -> BehaviorProfile:
        """
        Generate a behavior profile for the current state.
        
        Logic:
        1. Check Health: If health is low, probability of skipping is high.
        2. Random Skip: Small chance to just not do it (Simulate 'busy').
        3. Think Time: Humans pause before clicking/navigating.
        """
        now = datetime.now(timezone.utc)
        
        # 1. Skip Probability (Simulate distinterest or fear of detection)
        # If health is low (e.g. 0.5), skip chance increases.
        # Base skip chance: 5% (Humans miss things)
        skip_chance = 0.05
        if state.health_score < 0.8:
            skip_chance += (0.8 - state.health_score) * 0.5  # Up to +0.4 for very low health
        
        should_skip = random.random() < skip_chance
        
        if should_skip:
            return BehaviorProfile(
                should_skip=True,
                think_time_delay=0.0,
                next_scheduled_fetch=now + timedelta(minutes=random.randint(10, 60)),
                reason="simulated_skip"
            )

        # 2. Think Time (Micro-delays before action)
        # Random delay between 0.5s and 3.0s to avoid machine-speed requests upon scheduling trigger
        think_time = random.uniform(0.5, 3.0)
        
        # 3. Next Schedule Calculation
        # This is for the *subsequent* fetch, not the current one.
        next_fetch = self._calculate_next_fetch_time(state, now)

        return BehaviorProfile(
            should_skip=False,
            think_time_delay=think_time,
            next_scheduled_fetch=next_fetch,
            reason="standard_fetch"
        )
        
    def _calculate_next_fetch_time(self, state: SourceState, now: datetime) -> datetime:
        """
        Calculate sustainable next visit time.
        
        Rules:
        - Base: state.avg_interval
        - Jitter: +/- JITTER_FACTOR
        - Long Pause: 1% chance of a "coffee break" (1-4 hours silence)
        """
        # Base Interval + Jitter
        jitter_range = state.avg_interval * JITTER_FACTOR
        jitter_val = random.uniform(-jitter_range, jitter_range)
        interval = max(MIN_INTERVAL_SECONDS, state.avg_interval + jitter_val)
        
        next_time = now + timedelta(seconds=interval)
        
        # Occasional Long Pause (The "Coffee Break" or "Sleep" simulation)
        # 1% chance to disappear for a while. This breaks regular patterns significantly.
        if random.random() < 0.01:
            pause_minutes = random.randint(60, 240)
            next_time += timedelta(minutes=pause_minutes)
            logger.info(f"Source {state.source_id}: Applied long pause of {pause_minutes} minutes.")
            
        return next_time


class FetchScheduler:
    """
    The Clock. Orchestrates WHEN things happen based on State and Engine.
    
    Used by the runner loop to check if a source is ready.
    """
    
    def __init__(self, behavior_engine: BehaviorEngine = None):
        self.engine = behavior_engine or BehaviorEngine()
        
    def should_fetch_now(self, state: SourceState) -> bool:
        """
        Determines if a fetch should be attempted right now.
        
        Checks:
        - Cooldowns
        - Detailed timing (last_fetch + interval)
        """
        now = datetime.now(timezone.utc)
        
        # 1. Hard Constraints (Cooldowns)
        if state.is_cooling_down():
            return False
            
        # 2. Timing
        if not state.last_fetch_at:
            # Never fetched? Go for it (subject to Engine skip later)
            return True
        
        # Check against the simple average interval first as a gate
        # (The real next_time is hidden in the behavior logic, but checking strict interval 
        # prevents aggressive polling loops from hammering the Engine)
        if (now - state.last_fetch_at).total_seconds() < (state.avg_interval * (1 - JITTER_FACTOR)):
             return False

        return True

    def get_next_action(self, state: SourceState) -> BehaviorProfile:
        """
        Consult the BehaviorEngine for orders.
        Call this when `should_fetch_now` returns True.
        """
        return self.engine.generate_profile(state)

    def next_fetch_at(self, state: SourceState) -> datetime:
        """
        Predictive method for external schedulers (e.g. database job queue).
        Returns a SAFE time to schedule the next check.
        """
        if state.is_cooling_down():
            return state.cooldown_until
            
        if not state.last_fetch_at:
            return datetime.now(timezone.utc)
            
        # Return base prediction
        return state.last_fetch_at + timedelta(seconds=state.avg_interval)
