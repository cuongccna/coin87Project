from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPO_DIR = ROOT / "backend" / "app" / "repositories"

FORBIDDEN_SUBSTRINGS = [
    ".commit(",
    ".add(",
    ".delete(",
    ".flush(",
    "insert(",
    "update(",
    "delete(",
]


def test_repository_code_has_no_obvious_writes():
    files = list(REPO_DIR.glob("**/*.py"))
    assert files, "No repository files found."

    offenders: list[str] = []
    for f in files:
        txt = f.read_text(encoding="utf-8", errors="ignore")
        for s in FORBIDDEN_SUBSTRINGS:
            if s in txt:
                offenders.append(f"{f.relative_to(ROOT)} contains {s!r}")

    assert not offenders, "Read-only repository violations:\n" + "\n".join(offenders)

