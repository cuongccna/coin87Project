from __future__ import annotations

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.env import load_env_if_present
from ingestion.core.fetch_context import FetchContext
from ingestion.core.content_fetcher import fetch_and_extract
from ingestion.core.source_registry import load_sources_yaml


def main():
    load_env_if_present()
    cfg_path = Path(__file__).resolve().parents[1] / "ingestion" / "config" / "sources.yaml"
    registry = load_sources_yaml(cfg_path)
    # Pick a source with detailed_fetch true if present
    src = None
    for v in registry.sources:
        if getattr(v, 'detailed_fetch', False):
            src = v
            break
    if not src:
        # fallback to any RSS
        for v in registry.sources:
            if v.type == 'rss':
                src = v
                break
    ctx = FetchContext()
    url = input('URL to test (enter to use source.url): ').strip() or src.url
    html, text, meta = fetch_and_extract(url, ctx, src.key)
    print('META:', meta)
    print('STATUS:', meta.get('status'))
    print('EXCERPT:\n', meta.get('excerpt'))
    print('TEXT_SNIPPET:\n', (text or '')[:800])


if __name__ == '__main__':
    main()
