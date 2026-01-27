"""Ingestion core primitives for Job A.

Raw ingestion module for Coin87:
- Store raw data ONLY, no processing or scoring
- Generate content hash for deduplication
- Append-only: never update existing records
"""

from ingestion.core.raw_ingest import (
    IngestResult,
    RawIngestInput,
    RawIngestOutput,
    SourceType,
    compute_content_hash,
    ingest_raw,
    ingest_raw_batch,
)
from ingestion.core.network_client import NetworkClient
from ingestion.core.health import HealthMonitor, HealthStatus, ErrorType
from ingestion.core.circuit_breaker import CircuitBreaker, CircuitState
from ingestion.core.ingestion_controller import IngestionController
from ingestion.core.behavior import FetchScheduler

__all__ = [
    "IngestResult",
    "RawIngestInput",
    "RawIngestOutput",
    "SourceType",
    "compute_content_hash",
    "ingest_raw",
    "ingest_raw_batch",
    "NetworkClient",
    "HealthMonitor",
    "HealthStatus",
    "ErrorType",
    "CircuitBreaker",
    "CircuitState",
    "IngestionController",
    "FetchScheduler"
]
