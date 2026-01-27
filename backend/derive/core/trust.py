"""Source Trust Evolution (Phase 5).

Tracks how trust in information sources evolves over time based on reliability outcomes.
Strictly prohibits checking for market impact or predictive power.

Algorithm:
- Rolling window assessment (30 days default)
- Conservation of Trust (slow updates, max delta ±0.05)
- Reference to global baseline for persistence (lifespan)
- No punitive zeroing (floor 0.1)

Constraints:
- Deterministic
- No ML
- No price data

"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Mapping

from sqlalchemy import Float, func, select, and_
from sqlalchemy.orm import Session

from app.models.cluster_assignment import ClusterAssignment
from app.models.information_event import InformationEvent
from app.models.narrative_reliability_snapshot import NarrativeReliabilitySnapshot
from app.models.source_reliability import SourceReliability
from derive.core.reliability import ReliabilityStatus

logger = logging.getLogger(__name__)

UTC = timezone.utc

# Configuration (Locked)
TRUST_FLOOR = 0.1
TRUST_CEILING = 1.0
MAX_DELTA_PER_UPDATE = 0.05
ROLLING_WINDOW_DAYS = 30
GLOBAL_AVG_LIFESPAN_DEFAULT_MINS = 24 * 60  # Fallback 24h


@dataclass(frozen=True)
class SourceMetrics:
    source_ref: str
    total_mentions_in_window: int
    rolling_confirmed_rate: float
    rolling_noise_rate: float
    persistence_alignment: float
    
    # Legacy/Global stats (accumulated)
    # For now, we might just track the rolling window stats in this object
    
    
def calculate_trust_evolution(
    current_trust: float,
    metrics: SourceMetrics
) -> float:
    """Compute new trust index based on evolution rules."""
    
    # 1. Base Mix: Inertia (80%) + New Performance (20%)
    # "new_trust = old_trust * 0.8 + rolling_confirmed_rate * 0.2"
    mixed_trust = (current_trust * 0.8) + (metrics.rolling_confirmed_rate * 0.2)
    
    # 2. Noise Penalty
    # Small penalty from rolling_noise_rate
    # Example: if 100% noise, apply -0.1 penalty
    noise_penalty = metrics.rolling_noise_rate * 0.1
    
    # 3. Persistence Bonus/Malus
    # average lifespan of clusters mentioned by this source normalized against global average
    # Alignment 1.0 = Neutral.
    # Impact: Small bonus.
    persistence_effect = (metrics.persistence_alignment - 1.0) * 0.05
    # Cap persistence effect to Avoid huge swings
    persistence_effect = max(-0.05, min(0.05, persistence_effect))
    
    target_trust = mixed_trust - noise_penalty + persistence_effect
    
    # 4. Max Delta Constraint
    delta = target_trust - current_trust
    clamped_delta = max(-MAX_DELTA_PER_UPDATE, min(MAX_DELTA_PER_UPDATE, delta))
    
    final_trust = current_trust + clamped_delta
    
    # 5. Global Bounds [0.1, 1.0]
    return max(TRUST_FLOOR, min(TRUST_CEILING, final_trust))


def _compute_global_avg_lifespan(session: Session, since: datetime) -> float:
    """Calculate the average narrative lifespan across ALL sources in the window."""
    stmt = select(func.avg(NarrativeReliabilitySnapshot.lifespan_minutes)).where(
        NarrativeReliabilitySnapshot.snapshot_timestamp >= since
    )
    result = session.execute(stmt).scalar()
    return float(result) if result else GLOBAL_AVG_LIFESPAN_DEFAULT_MINS


def aggregate_source_metrics(db: Session) -> Mapping[str, SourceMetrics]:
    """Aggregate metrics for all sources using rolling window logic."""
    
    now = datetime.now(UTC)
    window_start = now - timedelta(days=ROLLING_WINDOW_DAYS)
    
    # Global Baseline
    global_avg_lifespan = _compute_global_avg_lifespan(db, window_start)
    if global_avg_lifespan <= 0:
        global_avg_lifespan = GLOBAL_AVG_LIFESPAN_DEFAULT_MINS

    # Get latest snapshot for each cluster within window
    # Subquery for latest timestamp per cluster
    latest_ts_sub = (
        select(
            NarrativeReliabilitySnapshot.cluster_id,
            func.max(NarrativeReliabilitySnapshot.snapshot_timestamp).label("max_ts")
        )
        .group_by(NarrativeReliabilitySnapshot.cluster_id)
        .subquery()
    )
    
    # Latest snapshots
    latest_snapshots = (
        select(
            NarrativeReliabilitySnapshot.cluster_id,
            NarrativeReliabilitySnapshot.reliability_status,
            NarrativeReliabilitySnapshot.lifespan_minutes
        )
        .join(
            latest_ts_sub,
            and_(
                NarrativeReliabilitySnapshot.cluster_id == latest_ts_sub.c.cluster_id,
                NarrativeReliabilitySnapshot.snapshot_timestamp == latest_ts_sub.c.max_ts
            )
        )
        .cte("latest_window_snapshots")
    )
    
    # Aggregation Query
    # Join Event -> Assignment -> Latest Snapshot
    # Filter by Event Created At (or Assignment Created At) >= Window Start?
    # Actually, we want to score sources based on RECENT activity.
    # So filter where ClusterAssignment.created_at >= window_start
    
    is_confirmed = func.case(
        (latest_snapshots.c.reliability_status.in_(
            [ReliabilityStatus.STRONG.value, ReliabilityStatus.MODERATE.value]
        ), 1),
        else_=0
    )
    
    is_noise = func.case(
        (latest_snapshots.c.reliability_status == ReliabilityStatus.NOISE.value, 1),
        else_=0
    )
    
    stmt = (
        select(
            InformationEvent.source_ref,
            func.count(InformationEvent.id).label("total"),
            func.sum(is_confirmed).label("confirmed"),
            func.sum(is_noise).label("noise"),
            func.avg(latest_snapshots.c.lifespan_minutes).label("avg_lifespan")
        )
        .join(ClusterAssignment, InformationEvent.id == ClusterAssignment.information_event_id)
        .join(latest_snapshots, ClusterAssignment.cluster_id == latest_snapshots.c.cluster_id)
        .where(ClusterAssignment.created_at >= window_start)
        .group_by(InformationEvent.source_ref)
    )
    
    rows = db.execute(stmt).all()
    results = {}
    
    for row in rows:
        total = row.total
        if total == 0:
            continue
            
        confirmed_rate = (row.confirmed or 0) / total
        noise_rate = (row.noise or 0) / total
        avg_lifespan = float(row.avg_lifespan or 0.0)
        
        persistence_alignment = avg_lifespan / global_avg_lifespan
        
        results[row.source_ref] = SourceMetrics(
            source_ref=row.source_ref,
            total_mentions_in_window=total,
            rolling_confirmed_rate=confirmed_rate,
            rolling_noise_rate=noise_rate,
            persistence_alignment=persistence_alignment
        )
        
    return results


def update_source_trust_scores(db: Session, metrics_map: Mapping[str, SourceMetrics]) -> int:
    """Update SourceReliability table with calculated scores."""
    count = 0
    for source_ref, metrics in metrics_map.items():
        
        # Get or create source record
        source_rec = db.get(SourceReliability, source_ref)
        if not source_rec:
            source_rec = SourceReliability(source_ref=source_ref)
            db.add(source_rec)
        
        # Calculate new trust using evolution logic
        new_trust = calculate_trust_evolution(source_rec.trust_index, metrics)
        
        # Update fields
        source_rec.trust_index = new_trust
        source_rec.rolling_confirmed_rate = metrics.rolling_confirmed_rate
        source_rec.rolling_noise_rate = metrics.rolling_noise_rate
        source_rec.persistence_alignment = metrics.persistence_alignment
        
        # We also update cumulative counters if we had them in input, 
        # but here we focus on the evolution metrics.
        # Ideally we'd increment total_mentions by new mentions, but inputs are rolling stats.
        # See note: "Update source_trust_metrics with: rolling_confirmed_rate..."
        
        count += 1
        
    return count
