from __future__ import annotations

"""Deduplication helpers (Job A).

Dedup rule (required):
- content_hash_sha256 = SHA256(normalized abstract + source_name)

Important:
- No business logic. This is purely deterministic normalization+hashing.
- Do not log raw content. Hash is safe for ops/audit.
"""

import hashlib


def compute_content_hash_sha256_bytes(*, abstract: str, source_name: str) -> bytes:
    normalized = (abstract or "").strip() + "\n" + (source_name or "").strip()
    return hashlib.sha256(normalized.encode("utf-8")).digest()


def compute_content_hash_sha256_hex(*, abstract: str, source_name: str) -> str:
    return compute_content_hash_sha256_bytes(abstract=abstract, source_name=source_name).hex()

