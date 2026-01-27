"""
Timekeeper module for Coin87.

COIN87 MANIFESTO LOCK:
"On Information, Trust, and Silence"

Time is a reliability primitive.
This module ensures all timestamps are:
1. Normalized to UTC.
2. Traceable to their source representation.
3. Rated for confidence (HIGH/MEDIUM/LOW).

No silent guessing. No corrupted timelines.
"""

from __future__ import annotations

import logging
import re
import email.utils
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from ingestion.core.time_common import TimeConfidence, TimeFormat, TimeRecord
from ingestion.core.relative_time import RelativeTimeResolver

logger = logging.getLogger(__name__)


class Timekeeper:
    """
    The authoritative source for time normalization in Coin87.
    """
    
    def __init__(self):
        self.relative_resolver = RelativeTimeResolver()

    def normalize(
        self, 
        raw_time: Union[str, int, float, None], 
        fetch_time_utc: datetime, 
        source_timezone: Optional[str] = None
    ) -> TimeRecord:
        """
        Main entry point. Converts any raw time input into a rigorous TimeRecord.
        
        Args:
            raw_time: The input timestamp (string, epoch, or None).
            fetch_time_utc: The exact time the data was fetched (MANDATORY).
            source_timezone: Optional context-aware timezone (e.g. "US/Eastern") if known.
                             Only used if the raw timestamp lacks timezone info.
                             
        Returns:
            TimeRecord: Normalized UTC time with metadata.
        """
        # Ensure fetch time is valid and timezone aware (UTC)
        if fetch_time_utc.tzinfo is None:
             raise ValueError("fetch_time_utc must be timezone-aware (UTC)")

        # 1. Handle Empty/Null -> Fallback
        if not raw_time or str(raw_time).strip() == "":
            return self._create_fallback_record(
                raw_time, 
                fetch_time_utc, 
                error="Empty or null input"
            )

        raw_str = str(raw_time).strip()

        # 2. Try Absolute Parsing (ISO, RFC, Epoch)
        # This is preferred as it yields highest confidence.
        try:
            absolute_record = self.parse_absolute(raw_str, source_timezone)
            if absolute_record:
                return absolute_record
        except Exception as e:
            # If absolute parsing crashed, note it but try relative
            pass

        # 3. Try Relative Parsing
        # Common in social media / news feeds ("2h ago")
        try:
            relative_record = self.relative_resolver.resolve(raw_str, fetch_time_utc)
            if relative_record:
                return relative_record
        except Exception as e:
            pass

        # 4. Fallback (Failed to parse)
        # If we can't understand the time, we MUST use fetch_time_utc
        # but mark it as LOW confidence / UNKNOWN format.
        return self._create_fallback_record(
            raw_str, 
            fetch_time_utc, 
            error="Unrecognized format"
        )

    def parse_absolute(self, raw_str: str, source_context_tz: Optional[str]) -> Optional[TimeRecord]:
        """Attempt to parse absolute date formats."""
        
        # A. Try ISO 8601 (2026-01-27T14:00:00+00:00)
        try:
            dt = datetime.fromisoformat(raw_str)
            fmt = TimeFormat.ABSOLUTE_ISO
            confidence = TimeConfidence.HIGH if dt.tzinfo else TimeConfidence.MEDIUM
            return self._finalize_absolute(dt, raw_str, fmt, confidence, source_context_tz)
        except ValueError:
            pass

        # B. Try RFC 822 / 1123 (Mon, 27 Jan 2026 14:00:00 GMT)
        try:
            # parsedate_to_datetime handles many email/http formats
            dt = email.utils.parsedate_to_datetime(raw_str)
            # If successfully parsed, it usually has tzinfo if the string had it
            fmt = TimeFormat.ABSOLUTE_RFC
            confidence = TimeConfidence.HIGH if dt.tzinfo else TimeConfidence.MEDIUM
            return self._finalize_absolute(dt, raw_str, fmt, confidence, source_context_tz)
        except Exception:
            pass

        # C. Try Epoch (Numeric)
        if raw_str.replace('.', '', 1).isdigit():
            try:
                val = float(raw_str)
                # heuristic: if > 3bb, might be millis
                if val > 1e11: 
                    val = val / 1000.0
                dt = datetime.fromtimestamp(val, tz=timezone.utc)
                return TimeRecord(
                    utc_timestamp=dt,
                    epoch_seconds=dt.timestamp(),
                    original_value=raw_str,
                    parsed_format=TimeFormat.EPOCH,
                    confidence=TimeConfidence.HIGH, # Epoch is effectively UTC
                    source_timezone="UTC"
                )
            except Exception:
                pass
                
        return None

    def _finalize_absolute(
        self, 
        dt: datetime, 
        original: str, 
        fmt: TimeFormat, 
        confidence_if_has_tz: TimeConfidence, 
        source_context_tz: Optional[str]
    ) -> TimeRecord:
        """Helper to attach timezone if missing and convert to UTC."""
        final_confidence = confidence_if_has_tz
        used_tz = None

        if dt.tzinfo is None:
            # Naive datetime.
            if source_context_tz:
                # We have a hint from configuration (e.g. "We know this site is EST")
                # Need external library like pytz or zoneinfo for full string support usually.
                # For this core module without extra deps, we are careful.
                # If we assume UTC because no library is present:
                dt = dt.replace(tzinfo=timezone.utc)
                used_tz = "UTC (Assumed)" # Or source_context_tz if we actually applied it
                
                # If we actually had a way to map source_context_tz to a tzinfo, we would.
                # Since we don't want to add `pytz` dependency just yet if not in requirements,
                # we assume UTC but note the ambiguity.
                final_confidence = TimeConfidence.MEDIUM
            else:
                # No hint. Must assume UTC.
                dt = dt.replace(tzinfo=timezone.utc)
                used_tz = "UTC (Default)"
                final_confidence = TimeConfidence.LOW # Dangerous assumption
        else:
            final_confidence = TimeConfidence.HIGH
            used_tz = str(dt.tzinfo)

        # Normalize to UTC
        utc_dt = dt.astimezone(timezone.utc)

        return TimeRecord(
            utc_timestamp=utc_dt,
            epoch_seconds=utc_dt.timestamp(),
            original_value=original,
            parsed_format=fmt,
            confidence=final_confidence,
            source_timezone=used_tz
        )

    def _create_fallback_record(self, raw_val: Any, fetch_time: datetime, error: str) -> TimeRecord:
        """Create a safety record when parsing fails completely."""
        return TimeRecord(
            utc_timestamp=fetch_time,
            epoch_seconds=fetch_time.timestamp(),
            original_value=str(raw_val) if raw_val else None,
            parsed_format=TimeFormat.UNKNOWN,
            confidence=TimeConfidence.LOW,
            reference_time=fetch_time,
            parse_errors=error
        )
