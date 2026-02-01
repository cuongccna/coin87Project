#!/usr/bin/env python3
"""Simple sample ingestion script for Inversion Feeds.

Usage:
  python ingest_inversion_sample.py --file sample_inversions.json [--api http://127.0.0.1:8000] [--token <TOKEN>] [--dry-run]

The script posts each JSON object in the file to POST /v1/inversion-feeds/ with Authorization Bearer token.
"""
import os
import sys
import json
import argparse
from typing import List

try:
    import requests
except Exception:
    print("Missing dependency 'requests'. Install with: pip install requests")
    sys.exit(1)


def load_items(path: str) -> List[dict]:
    # Support calling from repo root: if the provided path doesn't exist,
    # try resolving relative to this script's directory (backend/ingestion/jobs).
    if not os.path.exists(path):
        script_dir = os.path.dirname(__file__)
        alt = os.path.join(script_dir, path)
        if os.path.exists(alt):
            path = alt
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Input file not found: {path}")
        raise


def post_item(api_base: str, token: str, item: dict, dry_run: bool = False):
    url = api_base.rstrip("/") + "/v1/inversion-feeds/"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    if dry_run:
        print("DRY-RUN: would POST to", url, "payload=", json.dumps(item))
        return None

    resp = requests.post(url, headers=headers, json=item)
    try:
        data = resp.json()
    except Exception:
        data = resp.text
    return resp.status_code, data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="sample_inversions.json", help="Path to JSON file with array of feed objects")
    parser.add_argument("--api", default=os.environ.get("C87_API_BASE_URL") or os.environ.get("NEXT_PUBLIC_API_BASE_URL") or "http://127.0.0.1:8000", help="Backend API base URL")
    parser.add_argument("--token", default=os.environ.get("C87_UI_BEARER_TOKEN") or os.environ.get("NEXT_PUBLIC_UI_BEARER_TOKEN"), help="Bearer token (optional if API is open)")
    parser.add_argument("--dry-run", action="store_true", help="Do not perform HTTP requests, only print actions")

    args = parser.parse_args()

    items = load_items(args.file)
    if not isinstance(items, list):
        print("Input file must be a JSON array of objects")
        sys.exit(2)

    print(f"Posting {len(items)} items to {args.api} (dry_run={args.dry_run})")

    for idx, item in enumerate(items, start=1):
        print(f"[{idx}/{len(items)}] symbol={item.get('symbol')} feed_type={item.get('feed_type')}")
        if args.dry_run:
            post_item(args.api, args.token, item, dry_run=True)
            continue

        result = post_item(args.api, args.token, item, dry_run=False)
        if result is None:
            print("No result")
            continue
        status, body = result
        if 200 <= status < 300:
            print(f"OK {status}:", body)
        else:
            print(f"ERROR {status}:", body)


if __name__ == "__main__":
    main()
