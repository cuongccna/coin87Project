from __future__ import annotations

"""Source registry and YAML loader (Job A).

Trust & governance intent:
- Source on/off controllable without code changes.
- Execution order controlled by config priority.
- Disabled sources are skipped silently.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ingestion.core.fetch_context import SourceConfig


_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


@dataclass(frozen=True, slots=True)
class SourceRegistry:
    sources: list[SourceConfig]

    def enabled_sources(self) -> list[SourceConfig]:
        enabled = [s for s in self.sources if s.enabled]
        return sorted(enabled, key=lambda s: (_PRIORITY_RANK.get(s.priority, 9), s.key))


def load_sources_yaml(path: Path) -> SourceRegistry:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or "sources" not in raw or not isinstance(raw["sources"], dict):
        raise ValueError("Invalid sources.yaml: expected top-level mapping with 'sources'.")

    sources: list[SourceConfig] = []
    for key, cfg in raw["sources"].items():
        if not isinstance(cfg, dict):
            continue
        sources.append(
            SourceConfig(
                key=str(key),
                enabled=bool(cfg.get("enabled", False)),
                type=str(cfg.get("type", "")),
                url=str(cfg.get("url", "")),
                rate_limit_seconds=int(cfg.get("rate_limit_seconds", 10)),
                proxy=bool(cfg.get("proxy", False)),
                priority=str(cfg.get("priority", "low")),
                name=str(cfg.get("name")) if cfg.get("name") is not None else None,
            )
        )

    return SourceRegistry(sources=sources)

