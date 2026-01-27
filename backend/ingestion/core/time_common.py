"""
Common time models for Coin87.

Shared to avoid circular dependencies between Timekeeper and RelativeTimeResolver.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict

class TimeConfidence(str, Enum):
    """
    Confidence level in the accuracy of the normalized timestamp.
    """
    HIGH = "HIGH"      # Absolute time with explicit timezone.
    MEDIUM = "MEDIUM"  # Absolute time with inferred timezone or high-precision relative.
    LOW = "LOW"        # Ambiguous time, coarse relative ("yesterday"), or fallback.


class TimeFormat(str, Enum):
    """
    The format category of the input timestamp.
    """
    ABSOLUTE_ISO = "absolute_iso"
    ABSOLUTE_RFC = "absolute_rfc" # RFC 822/1123
    EPOCH = "epoch"
    RELATIVE = "relative"
    UNKNOWN = "unknown"


class TimeRecord(BaseModel):
    """
    The canonical output of the Timekeeper.
    Contains the normalized time and all metadata required for auditing.
    """
    utc_timestamp: datetime
    epoch_seconds: float
    
    original_value: Optional[str]
    parsed_format: TimeFormat
    confidence: TimeConfidence
    
    source_timezone: Optional[str] = None
    reference_time: Optional[datetime] = None  # If relative, what was it relative to?
    parse_errors: Optional[str] = None
    
    model_config = ConfigDict(frozen=True)
