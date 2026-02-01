"""SQLAlchemy models package.

Institutional requirement:
- All ORM classes must be registered deterministically so mapper configuration
  cannot fail at runtime depending on import order.
"""

# Import all model modules to register mapped classes in SQLAlchemy's registry.
# This avoids runtime mapper failures (e.g., relationship string resolution).

from app.models import (  # noqa: F401
    cluster_assignment,
    consensus_pressure,
    decision_context,
    decision_environment_snapshot,
    decision_impact_record,
    decision_risk_event,
    information_event,
    inversion_feed,
    narrative,
    narrative_cluster,

    narrative_reliability_snapshot,
    re_evaluation_log,
    source_health,
    source_reliability,
    timing_distortion,
)

