from __future__ import annotations

"""Deterministic, rule-based risk detection for Job B.

STRICT:
- No ML, no external APIs.
- Conservative severity (low by default).
- Escalation requires repeated evidence (within current run batch only).
"""

import re
from dataclasses import dataclass
from typing import Any, Iterable, Optional

import yaml

from app.models.decision_risk_event import RecommendedPosture, RiskType


@dataclass(frozen=True, slots=True)
class RiskHit:
    risk_type: RiskType
    severity: int
    affected_decisions: list[str]
    recommended_posture: RecommendedPosture
    reason: str  # deterministic explanation for audit (no sentiment)
    narrative_theme: Optional[str] = None


@dataclass(frozen=True, slots=True)
class Ruleset:
    version: str
    narrative_rules: list[dict[str, Any]]
    timing_rules: list[dict[str, Any]]
    consensus_rules: list[dict[str, Any]]


def _load_yaml(path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("rules yaml must be a mapping")
    return raw


def load_rules(*, narrative_path, timing_path, consensus_path) -> Ruleset:
    n = _load_yaml(narrative_path)
    t = _load_yaml(timing_path)
    c = _load_yaml(consensus_path)

    version = str(n.get("version") or t.get("version") or c.get("version") or "0")
    return Ruleset(
        version=version,
        narrative_rules=list(n.get("narratives") or []),
        timing_rules=list(t.get("timing_distortion") or []),
        consensus_rules=list(c.get("consensus_pressure") or []),
    )


def _compile_keywords(keywords: Iterable[str]) -> list[re.Pattern[str]]:
    pats: list[re.Pattern[str]] = []
    for k in keywords:
        k = str(k).strip()
        if not k:
            continue
        pats.append(re.compile(re.escape(k), re.IGNORECASE))
    return pats


def _match_any(pats: list[re.Pattern[str]], text: str) -> bool:
    for p in pats:
        if p.search(text):
            return True
    return False


def _safe_int(v: Any, default: int) -> int:
    try:
        return int(v)
    except Exception:  # noqa: BLE001
        return default


def _clamp_severity(v: int) -> int:
    return max(1, min(5, int(v)))

 
def _posture(value: Any, default: RecommendedPosture) -> RecommendedPosture:
    """Defensive enum parsing (never raise)."""
    try:
        return RecommendedPosture(str(value))
    except Exception:  # noqa: BLE001
        return default


def detect_risks_for_event(
    *,
    text: str,
    rules: Ruleset,
    seen_counts: dict[str, int],
) -> list[RiskHit]:
    """Return RiskHit list for one event based on deterministic keyword rules.

    seen_counts is a run-local counter keyed by rule_id to support conservative escalation.
    """
    hits: list[RiskHit] = []
    t = (text or "").strip()
    if not t:
        return hits

    # Narrative contamination rules
    for r in rules.narrative_rules:
        rule_id = str(r.get("id") or r.get("theme") or "narrative")
        pats = _compile_keywords(r.get("keywords") or [])
        if not pats or not _match_any(pats, t):
            continue

        seen_counts[rule_id] = seen_counts.get(rule_id, 0) + 1
        base = _safe_int(r.get("base_severity"), 1)
        # Escalate very conservatively within run: +1 per 3 repeats.
        sev = base + ((seen_counts[rule_id] - 1) // 3)
        sev = _clamp_severity(sev)

        affected = [str(x) for x in (r.get("affected_decisions") or ["allocation"])][:6]
        posture = _posture(r.get("posture") or "REVIEW", RecommendedPosture.REVIEW)
        theme = str(r.get("theme") or "Unspecified narrative").strip()

        hits.append(
            RiskHit(
                risk_type=RiskType.NARRATIVE_CONTAMINATION,
                severity=sev,
                affected_decisions=affected,
                recommended_posture=posture,
                reason=f"keyword_match(narrative_rule_id={rule_id})",
                narrative_theme=theme,
            )
        )

    # Consensus pressure rules -> CONSENSUS_TRAP
    for r in rules.consensus_rules:
        rule_id = str(r.get("id") or r.get("name") or "consensus")
        pats = _compile_keywords(r.get("keywords") or [])
        if not pats or not _match_any(pats, t):
            continue
        seen_counts[rule_id] = seen_counts.get(rule_id, 0) + 1
        base = _safe_int(r.get("base_severity"), 1)
        sev = base + ((seen_counts[rule_id] - 1) // 4)
        sev = _clamp_severity(sev)
        affected = [str(x) for x in (r.get("affected_decisions") or ["sizing"])][:6]
        posture = _posture(r.get("posture") or "REVIEW", RecommendedPosture.REVIEW)
        hits.append(
            RiskHit(
                risk_type=RiskType.CONSENSUS_TRAP,
                severity=sev,
                affected_decisions=affected,
                recommended_posture=posture,
                reason=f"keyword_match(consensus_rule_id={rule_id})",
            )
        )

    # Timing distortion rules
    for r in rules.timing_rules:
        rule_id = str(r.get("id") or r.get("name") or "timing")
        pats = _compile_keywords(r.get("keywords") or [])
        if not pats or not _match_any(pats, t):
            continue
        seen_counts[rule_id] = seen_counts.get(rule_id, 0) + 1
        base = _safe_int(r.get("base_severity"), 1)
        sev = base + ((seen_counts[rule_id] - 1) // 4)
        sev = _clamp_severity(sev)
        affected = [str(x) for x in (r.get("affected_decisions") or ["timing"])][:6]
        posture = _posture(r.get("posture") or "DELAY", RecommendedPosture.DELAY)
        hits.append(
            RiskHit(
                risk_type=RiskType.TIMING_DISTORTION,
                severity=sev,
                affected_decisions=affected,
                recommended_posture=posture,
                reason=f"keyword_match(timing_rule_id={rule_id})",
            )
        )

    return hits

