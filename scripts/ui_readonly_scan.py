"""Static UI read-only scan (no backend required).

Checks:
- No POST/PUT/PATCH/DELETE usage in UI fetch calls
- No setInterval polling loops

This is intentionally conservative and string-based (trust validation).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TARGET_DIRS = [
    ROOT / "frontend",
    ROOT / "institutional-ui" / "src",
]

FILE_GLOBS = ["**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx"]

FORBIDDEN_PATTERNS = [
    (re.compile(r"\bfetch\([^)]*\{\s*[^}]*\bmethod\s*:\s*['\"]POST['\"]", re.I | re.S), "fetch POST"),
    (re.compile(r"\bfetch\([^)]*\{\s*[^}]*\bmethod\s*:\s*['\"]PUT['\"]", re.I | re.S), "fetch PUT"),
    (re.compile(r"\bfetch\([^)]*\{\s*[^}]*\bmethod\s*:\s*['\"]PATCH['\"]", re.I | re.S), "fetch PATCH"),
    (re.compile(r"\bfetch\([^)]*\{\s*[^}]*\bmethod\s*:\s*['\"]DELETE['\"]", re.I | re.S), "fetch DELETE"),
    (re.compile(r"\baxios\.(post|put|patch|delete)\b", re.I), "axios write"),
    (re.compile(r"\bsetInterval\s*\(", re.I), "setInterval polling"),
]


def iter_source_files(base: Path):
    for glob in FILE_GLOBS:
        for p in base.glob(glob):
            if p.is_file():
                yield p


def scan() -> int:
    failures: list[str] = []
    scanned = 0

    for base in TARGET_DIRS:
        if not base.exists():
            continue
        for path in iter_source_files(base):
            scanned += 1
            text = path.read_text(encoding="utf-8", errors="ignore")
            for rx, label in FORBIDDEN_PATTERNS:
                if rx.search(text):
                    failures.append(f"{label}: {path.relative_to(ROOT)}")

    print(f"Scanned {scanned} files.")
    if failures:
        print("FAIL: UI read-only violations detected:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("PASS: UI appears read-only (no write HTTP methods; no polling intervals).")
    return 0


if __name__ == "__main__":
    raise SystemExit(scan())

