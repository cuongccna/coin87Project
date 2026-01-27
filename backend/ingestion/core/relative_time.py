"""
Relative Time Resolver for Coin87.

COIN87 MANIFESTO LOCK:
"On Information, Trust, and Silence"

Handles the conversion of fuzzy, context-dependent time strings
into derived UTC timestamps.

Strictly adheres to:
- No exactness pretense (Confidence is capped at MEDIUM).
- Context requirement (Must have reference time).
- Unambiguous rejection of future/unknown formats.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from ingestion.core.time_common import TimeConfidence, TimeFormat, TimeRecord

logger = logging.getLogger(__name__)


class RelativeTimeResolver:
    """
    Sub-module for resolving relative time expressions.
    
    Prioritizes correctness over coverage. If a phrase is ambiguous
    (e.g., "a while ago"), it rejects it rather than guessing.
    """

    # --- Strict Regex Patterns ---
    
    # "5 minutes ago", "1 day ago"
    # Capture groups: 1=Amount, 2=Unit
    _NUMERIC_AGO = re.compile(
        r'(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago', 
        re.IGNORECASE
    )
    
    # "Just now", "moments ago"
    _FUZZY_NOW = re.compile(
        r'^(just now|moments ago|seconds ago|now)$', 
        re.IGNORECASE
    )
    
    # Specific day markers
    _YESTERDAY = re.compile(r'^yesterday.*', re.IGNORECASE)
    _LAST_NIGHT = re.compile(r'^last night.*', re.IGNORECASE)
    _EARLIER_TODAY = re.compile(r'^earlier today.*', re.IGNORECASE)

    # Rejection patterns (Future or too vague)
    _REJECT_PATTERNS = [
        re.compile(r'in \d+ \w+', re.IGNORECASE), # "in 5 minutes"
        re.compile(r'tomorrow', re.IGNORECASE),
        re.compile(r'a while ago', re.IGNORECASE),
        re.compile(r'recently', re.IGNORECASE),
        re.compile(r'soon', re.IGNORECASE),
    ]

    def resolve(self, raw_str: str, reference_time_utc: datetime) -> Optional[TimeRecord]:
        """
        Attempt to resolve a relative time string.
        
        Args:
            raw_str: The string to parse.
            reference_time_utc: The anchor time (usually fetch time).
                                Must be timezone aware (UTC).
                                
        Returns:
            TimeRecord if resolved, None if pattern not matched.
        """
        if reference_time_utc.tzinfo is None:
             raise ValueError("reference_time_utc must be timezone-aware")
             
        text = raw_str.strip()
        
        # 1. Check Rejections
        for pattern in self._REJECT_PATTERNS:
            if pattern.search(text):
                logger.debug(f"Rejected relative time '{text}': Too vague or future.")
                return None

        # 2. Check "Just Now" (Low Confidence)
        if self._FUZZY_NOW.search(text):
            return self._build_record(
                derived_time=reference_time_utc,
                original=text,
                reference=reference_time_utc,
                confidence=TimeConfidence.LOW # Fuzzy
            )

        # 3. Check Numeric Ago (Medium Confidence)
        match = self._NUMERIC_AGO.search(text)
        if match:
            amount = int(match.group(1))
            unit = match.group(2).lower()
            
            # Compute Delta
            try:
                delta = self._get_delta(amount, unit)
            except ValueError:
                return None # Unknown unit
                
            # Stale Inference Check
            # If > 30 days, confidence drops to LOW
            derived_time = reference_time_utc - delta
            confidence = TimeConfidence.MEDIUM
            
            if delta > timedelta(days=30):
                confidence = TimeConfidence.LOW
                
            return self._build_record(
                derived_time=derived_time,
                original=text,
                reference=reference_time_utc,
                confidence=confidence
            )

        # 4. Check "Yesterday" / "Last Night" (Low Confidence)
        # We assume 24h ago primarily, or start of yesterday?
        # "Yesterday" context is usually "Posted Yesterday". 
        # Safest "derived" time is -24h with Low Confidence to indicate lack of precision.
        if self._YESTERDAY.search(text) or self._LAST_NIGHT.search(text):
            derived_time = reference_time_utc - timedelta(days=1)
            return self._build_record(
                derived_time=derived_time,
                original=text,
                reference=reference_time_utc,
                confidence=TimeConfidence.LOW
            )
            
        if self._EARLIER_TODAY.search(text):
            # Extremely vague. Maybe 3 hours ago? 
            # Better to reject? Or assume reasonably recent?
            # Prompt says "Support ... 'earlier today'".
            # We'll use -4 hours as a heuristic and mark LOW.
            derived_time = reference_time_utc - timedelta(hours=4)
            return self._build_record(
                derived_time=derived_time,
                original=text,
                reference=reference_time_utc,
                confidence=TimeConfidence.LOW
            )

        return None

    def _get_delta(self, amount: int, unit: str) -> timedelta:
        """Calculate timedelta from unit."""
        if unit.startswith('second'):
            return timedelta(seconds=amount)
        if unit.startswith('minute'):
            return timedelta(minutes=amount)
        if unit.startswith('hour'):
            return timedelta(hours=amount)
        if unit.startswith('day'):
            return timedelta(days=amount)
        if unit.startswith('week'):
            return timedelta(weeks=amount)
        if unit.startswith('month'):
            return timedelta(days=amount * 30) # Approx
        if unit.startswith('year'):
            return timedelta(days=amount * 365) # Approx
        raise ValueError(f"Unknown unit: {unit}")

    def _build_record(
        self, 
        derived_time: datetime, 
        original: str, 
        reference: datetime, 
        confidence: TimeConfidence
    ) -> TimeRecord:
        """Helper to construct the TimeRecord."""
        return TimeRecord(
            utc_timestamp=derived_time,
            epoch_seconds=derived_time.timestamp(),
            original_value=original,
            parsed_format=TimeFormat.RELATIVE,
            confidence=confidence,
            reference_time=reference,
            source_timezone="UTC (Derived)"
        )
