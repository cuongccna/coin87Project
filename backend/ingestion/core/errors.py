from __future__ import annotations

"""Controlled ingestion errors for Job A.

Trust & governance intent:
- Job A must be failure-tolerant and never crash the system.
- Adapters must swallow their own exceptions and return partial success.
- These errors are *signals* for logging and control flow, not reasons to abort Job A.
"""


class IngestionError(RuntimeError):
    """Base error for ingestion; should be caught and logged, not propagated."""


class FetchError(IngestionError):
    """Raised when a source fetch fails (network, HTTP, parse)."""


class NormalizeError(IngestionError):
    """Raised when an item cannot be normalized into an insertable event."""


class ValidationError(IngestionError):
    """Raised when a normalized event fails validation."""


class InsertError(IngestionError):
    """Raised when insert fails for non-dedup reasons."""

