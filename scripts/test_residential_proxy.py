#!/usr/bin/env python3
"""Quick test: fetch a single source via FetchContext to validate residential proxy pool.
Usage: python scripts/test_residential_proxy.py [source_key]

Default source_key: coindesk_rss
"""
from pathlib import Path
import sys
import os

# Ensure backend on path
BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from ingestion.core.source_registry import load_sources_yaml
from ingestion.core.fetch_context import FetchContext


def main():
    src_key = sys.argv[1] if len(sys.argv) > 1 else "coindesk_rss"

    cfg_path = Path(__file__).resolve().parents[1] / "backend" / "ingestion" / "config" / "sources.yaml"
    print(f"Loading sources from: {cfg_path}")
    registry = load_sources_yaml(cfg_path)

    source = None
    for s in registry.enabled_sources():
        if s.key == src_key:
            source = s
            break

    if not source:
        print(f"Source with key '{src_key}' not found or not enabled.")
        return 2

    print(f"Testing fetch for source: {source.key} -> {source.url} (tier={source.tier}, proxy={source.proxy})")

    ctx = FetchContext()
    status, text, meta = ctx.fetch_text(source=source)

    print("--- META ---")
    for k, v in meta.items():
        print(f"{k}: {v}")
    print("--- STATUS ---")
    print(status)

    if text:
        snippet = text[:1000].replace('\n', ' ')  # single-line snippet
        print("--- BODY SNIPPET ---")
        print(snippet)
    else:
        print("No body returned (None or empty).")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
