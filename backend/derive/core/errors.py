from __future__ import annotations

"""Controlled errors for Job B (derive risk).

Trust & governance intent:
- Job B must not crash on one bad event.
- Errors are logged and processing continues (partial success is success).
"""


class DeriveError(RuntimeError):
    """Base error for derive pipeline; should be caught and logged, not propagated."""


class RuleLoadError(DeriveError):
    """Raised when rule YAML cannot be loaded/parsed."""


class DetectError(DeriveError):
    """Raised when deterministic detection fails for an event."""


class PersistenceError(DeriveError):
    """Raised when DB insert/update fails for a derived artifact."""

