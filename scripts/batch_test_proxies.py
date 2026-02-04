#!/usr/bin/env python3
"""Batch test enabled sources via FetchContext and report stats.
Usage: python scripts/batch_test_proxies.py
"""
from pathlib import Path
import sys
import time

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from ingestion.core.source_registry import load_sources_yaml
from ingestion.core.fetch_context import FetchContext


def classify(meta, status):
    if status == 200:
        return 'success'
    if status == 304:
        return 'not_modified'
    if status in (403,):
        return 'hard_block'
    if status in (429,):
        return 'soft_block'
    if status is None:
        # meta may include proxy_failed or fallback_error
        if meta.get('proxy_failed'):
            return 'proxy_failed'
        return 'error'
    if status >= 400:
        return 'failed'
    return 'other'


def main():
    cfg_path = Path(__file__).resolve().parents[1] / 'backend' / 'ingestion' / 'config' / 'sources.yaml'
    registry = load_sources_yaml(cfg_path)
    sources = registry.enabled_sources()

    ctx = FetchContext()

    stats = {
        'total': 0,
        'success': 0,
        'not_modified': 0,
        'hard_block': 0,
        'soft_block': 0,
        'proxy_failed': 0,
        'failed': 0,
        'error': 0,
        'other': 0,
    }

    results = []

    for s in sources:
        stats['total'] += 1
        print(f"Testing: {s.key} -> {s.url} (tier={s.tier}, proxy={s.proxy})")
        start = time.time()
        status, text, meta = ctx.fetch_text(source=s)
        took = time.time() - start
        cls = classify(meta, status)
        stats[cls] = stats.get(cls, 0) + 1
        line = {
            'key': s.key,
            'url': s.url,
            'status': status,
            'class': cls,
            'proxy': meta.get('proxy'),
            'proxy_failed': meta.get('proxy_failed', False),
            'proxy_error': meta.get('proxy_error'),
            'took': round(took, 2),
        }
        results.append(line)
        print(f"  -> {cls} status={status} proxy={line['proxy']} took={line['took']}s proxy_failed={line['proxy_failed']}")

    print('\n=== SUMMARY ===')
    for k, v in stats.items():
        print(f"{k}: {v}")

    print('\n=== DETAILED RESULTS (first 50) ===')
    for r in results[:50]:
        print(r)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
