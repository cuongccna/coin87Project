from __future__ import annotations

"""Controlled errors for Job C (snapshot environment).

Trust & governance intent:
- Job C must not crash the system.
- A snapshot failure must not partially insert.
- Errors are logged and the job exits safely.
"""


class SnapshotError(RuntimeError):
    """Base error for snapshot pipeline; should be caught and logged."""


class AggregationError(SnapshotError):
    """Raised when risk aggregation fails."""


class EvaluationError(SnapshotError):
    """Raised when environment state evaluation fails."""


class PersistenceError(SnapshotError):
    """Raised when snapshot persistence fails."""

