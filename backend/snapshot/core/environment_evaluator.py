from __future__ import annotations

"""Environment evaluator for Job C.

Deterministic, conservative rules.

Key intent:
- Default to CLEAN.
- Escalate cautiously.
- Use narratives as indirect context only.
- Avoid aggressive downgrades by applying minimal hysteresis versus last snapshot.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.models.decision_environment_snapshot import EnvironmentState
from snapshot.core.risk_aggregator import AggregatedSignals


UTC = timezone.utc


@dataclass(frozen=True, slots=True)
class EvaluatedEnvironment:
    environment_state: EnvironmentState
    risk_density: int
    dominant_risks: list[str]


def _clamp_density(n: int) -> int:
    # "reasonable range" clamp
    return max(0, min(50, int(n)))


def _base_state(sig: AggregatedSignals) -> EnvironmentState:
    density = sig.active_risk_count

    # CONTAMINATED
    if sig.any_high_severity:
        return EnvironmentState.CONTAMINATED
    if sig.medium_category_count >= 2:
        return EnvironmentState.CONTAMINATED
    if sig.narrative_active_high_saturation:
        return EnvironmentState.CONTAMINATED

    # CAUTION
    if sig.medium_category_count >= 1:
        return EnvironmentState.CAUTION
    if sig.timing_distortion_present:
        return EnvironmentState.CAUTION
    if density >= 3:
        return EnvironmentState.CAUTION
    if sig.narrative_active_elevated:
        return EnvironmentState.CAUTION

    return EnvironmentState.CLEAN


def _apply_hysteresis(
    *,
    computed: EnvironmentState,
    last_state: Optional[EnvironmentState],
    last_snapshot_time: Optional[datetime],
    now: datetime,
) -> EnvironmentState:
    """Prevent aggressive downgrades (conservative governance stance).

    If the last state was CONTAMINATED very recently, do not drop directly to CLEAN.
    """
    if last_state is None or last_snapshot_time is None:
        return computed

    # Only apply within a short window; beyond that, allow natural downgrade.
    if now - last_snapshot_time > timedelta(hours=1):
        return computed

    if last_state == EnvironmentState.CONTAMINATED and computed == EnvironmentState.CLEAN:
        return EnvironmentState.CAUTION

    return computed


def evaluate(
    *,
    snapshot_time: datetime,
    signals: AggregatedSignals,
    last_state: Optional[EnvironmentState] = None,
    last_snapshot_time: Optional[datetime] = None,
) -> EvaluatedEnvironment:
    density = _clamp_density(signals.active_risk_count)
    dominant = list(signals.dominant_risk_categories)[:3]

    computed = _base_state(signals)
    computed = _apply_hysteresis(
        computed=computed,
        last_state=last_state,
        last_snapshot_time=last_snapshot_time,
        now=snapshot_time,
    )

    return EvaluatedEnvironment(environment_state=computed, risk_density=density, dominant_risks=dominant)

