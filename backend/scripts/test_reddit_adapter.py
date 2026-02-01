from __future__ import annotations

from pathlib import Path
import sys

# Ensure backend/ on sys.path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ingestion.adapters.reddit_adapter import RedditAdapter
from ingestion.core.fetch_context import FetchContext
from ingestion.core.source_registry import load_sources_yaml


def main(source_key: str = "reddit_cryptocurrency"):
    cfg_path = Path(__file__).resolve().parents[1] / "ingestion" / "config" / "sources.yaml"
    registry = load_sources_yaml(cfg_path)
    source = next((s for s in registry.sources if s.key == source_key), None)
    if source is None:
        print(f"Source {source_key} not found in {cfg_path}")
        return 1

    adapter = RedditAdapter()
    ctx = FetchContext()

    print(f"Testing RedditAdapter.fetch for source: {source.key} ({source.name}) url={source.url}")
    items = adapter.fetch(ctx, source)
    print(f"Fetched {len(items)} raw items")

    samples = items[:5]
    for i, it in enumerate(samples, 1):
        print(f"--- item {i} source_key={it.source_key}")
        payload = it.payload
        print(f"id={payload.get('id')} title={payload.get('title')[:120]!r}")

    # Try normalize/validate on first item
    if items:
        ne = adapter.normalize(items[0], source)
        print("Normalized event:")
        print(f"  source_id={ne.source_id}")
        print(f"  event_time={ne.event_time}")
        print(f"  abstract (len)={len(ne.abstract) if ne.abstract else 0}")
        print(f"  content_hash={ne.content_hash_sha256}")
        print(f"  validate={adapter.validate(ne)}")
    else:
        print("No items fetched — check REDDIT_CLIENT_ID/SECRET are set and network access")

    return 0


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--source', default='reddit_cryptocurrency')
    args = p.parse_args()
    raise SystemExit(main(args.source))
