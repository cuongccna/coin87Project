"""Rule-based reliability classification.

Deterministic logic to classify Information Clusters based on aggregated metrics.
Strictly avoids ML black-box logic.

Classification Levels:
- STRONG: High multi-source confirmation + persistence.
- MODERATE: Some confirmation, lower persistence.
- WEAK: Single source or very low persistence.
- NOISE: Spam-like patterns (high volume, zero diversity).

Coin87 Philosophy:
- Deterministic
- Explainable
- Information Behavior based (not market impact)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from derive.core.aggregation import ClusterMetrics


class ReliabilityStatus(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    NOISE = "NOISE"


@dataclass(frozen=True)
class ReliabilityResult:
    status: ReliabilityStatus
    score: float  # 0.0 to 10.0
    reasoning: list[str]  # Explainable factors


class ReliabilityClassifier:
    """Deterministic classifier for cluster reliability."""

    def classify(self, metrics: ClusterMetrics) -> ReliabilityResult:
        """Apply rules to determine reliability status and score."""
        
        score_components = []
        reasoning = []
        
        # 1. Source Volume (Base Score) - Max 3.0
        # More sources = higher reliability
        if metrics.source_count >= 10:
            score_components.append(3.0)
            reasoning.append("High source volume (10+)")
        elif metrics.source_count >= 5:
            score_components.append(2.0)
            reasoning.append("Moderate source volume (5+)")
        elif metrics.source_count >= 2:
            score_components.append(1.0)
            reasoning.append("Low multi-source confirmation (2+)")
        else:
            score_components.append(0.0)
            reasoning.append("Single source only")

        # 2. Source Diversity (Multiplier) - Max 2.0
        # Different platforms (twitter vs rss vs telegram) matter
        if metrics.source_diversity_count >= 3:
            score_components.append(2.0)
            reasoning.append("High platform diversity (3+ types)")
        elif metrics.source_diversity_count >= 2:
            score_components.append(1.0)
            reasoning.append("Moderate platform diversity (2 types)")
        else:
            reasoning.append("Low platform diversity")

        # 3. Persistence / Lifespan - Max 3.0
        # Flash-in-the-pan is less reliable than sustained narrative
        if metrics.lifespan_minutes >= 240: # 4 hours
            score_components.append(3.0)
            reasoning.append("High persistence (>4h)")
        elif metrics.lifespan_minutes >= 60: # 1 hour
            score_components.append(2.0)
            reasoning.append("Moderate persistence (>1h)")
        elif metrics.lifespan_minutes >= 15: # 15 mins
            score_components.append(1.0)
            reasoning.append("Low persistence (>15m)")
        else:
            reasoning.append("Very low persistence (<15m)")

        # 4. Remention Velocity (Bonus/Penalty) - Max 2.0
        # Too high velocity with low diversity = bot spam/noise
        if metrics.remention_rate_per_hour > 50 and metrics.source_diversity_count == 1:
            score_components.append(-2.0) # Penalty
            reasoning.append("High velocity single-source (Spam pattern)")
        elif metrics.remention_rate_per_hour > 10:
             score_components.append(2.0)
             reasoning.append("High active discussion velocity")
        elif metrics.remention_rate_per_hour > 2:
             score_components.append(1.0) # Moderate activity

        # Calculate Final Score
        raw_score = sum(score_components)
        final_score = max(0.0, min(10.0, raw_score)) # Clamp 0-10

        # Determine Status
        status = ReliabilityStatus.WEAK
        
        # Noise Filter
        if metrics.source_count == 1 and metrics.event_count > 10 and metrics.lifespan_minutes < 5:
             status = ReliabilityStatus.NOISE
             reasoning.append("CLASSIFICATION: NOISE (Single source spam burst)")
        elif final_score >= 7.0:
            status = ReliabilityStatus.STRONG
        elif final_score >= 4.0:
            status = ReliabilityStatus.MODERATE
        else:
            status = ReliabilityStatus.WEAK

        return ReliabilityResult(
            status=status,
            score=final_score,
            reasoning=reasoning
        )
