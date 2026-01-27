from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.information_event import InformationEvent
from app.models.decision_risk_event import DecisionRiskEvent, DecisionRiskImmutabilityError, RiskType, RecommendedPosture
from app.models.decision_environment_snapshot import DecisionEnvironmentSnapshot, DecisionEnvironmentSnapshotImmutabilityError, EnvironmentState
from app.models.decision_context import DecisionContext, DecisionContextType, DecisionContextMutationError
from app.models.decision_impact_record import DecisionImpactRecord, DecisionImpactImmutabilityError


UTC = timezone.utc


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _sha() -> bytes:
    return b"\x00" * 32


def seed_information_event(db: Session) -> InformationEvent:
    ev = InformationEvent(
        source_ref="test_source",
        external_ref=str(uuid.uuid4()),
        canonical_url=None,
        title="Test event",
        body_excerpt="excerpt",
        raw_payload={"kind": "test"},
        content_hash_sha256=_sha(),
        event_time=_now(),
        observed_at=_now(),
    )
    db.add(ev)
    db.flush()
    return ev


def seed_decision_risk_event(db: Session, info: InformationEvent) -> DecisionRiskEvent:
    t = _now()
    r = DecisionRiskEvent(
        information_event_id=info.id,
        risk_type=RiskType.CONSENSUS_TRAP,
        severity=3,
        affected_decisions=["allocation", "sizing"],
        recommended_posture=RecommendedPosture.REVIEW,
        detected_at=t,
        valid_from=t,
        valid_to=t + timedelta(hours=2),
    )
    db.add(r)
    db.flush()
    return r


def test_decision_risk_event_severity_update_forbidden(db_session: Session):
    info = seed_information_event(db_session)
    risk = seed_decision_risk_event(db_session, info)
    db_session.commit()

    risk.severity = 5
    with pytest.raises(DecisionRiskImmutabilityError):
        db_session.flush()

    db_session.rollback()
    persisted = db_session.get(DecisionRiskEvent, risk.id)
    assert persisted is not None
    assert persisted.severity == 3


def test_decision_risk_event_delete_forbidden(db_session: Session):
    info = seed_information_event(db_session)
    risk = seed_decision_risk_event(db_session, info)
    db_session.commit()

    db_session.delete(risk)
    with pytest.raises(DecisionRiskImmutabilityError):
        db_session.flush()


def test_environment_snapshot_update_forbidden(db_session: Session):
    snap = DecisionEnvironmentSnapshot(
        snapshot_time=_now(),
        environment_state=EnvironmentState.CLEAN,
        dominant_risks=[],
        risk_density=0,
    )
    db_session.add(snap)
    db_session.commit()

    snap.risk_density = 1
    with pytest.raises(DecisionEnvironmentSnapshotImmutabilityError):
        db_session.flush()


def test_impact_record_update_forbidden(db_session: Session):
    ctx = DecisionContext(context_type=DecisionContextType.IC_MEETING, context_time=_now(), description=None)
    db_session.add(ctx)
    db_session.flush()

    rec = DecisionImpactRecord(
        decision_context_id=ctx.id,
        environment_snapshot_id=None,
        qualitative_outcome="Reflection",
        learning_flags=["timing_error"],
    )
    db_session.add(rec)
    db_session.commit()

    rec.qualitative_outcome = "Changed"
    with pytest.raises(DecisionImpactImmutabilityError):
        db_session.flush()


def test_decision_context_core_fields_immutable_description_append_only(db_session: Session):
    ctx = DecisionContext(
        context_type=DecisionContextType.PM_REVIEW,
        context_time=_now(),
        description="Initial.",
    )
    db_session.add(ctx)
    db_session.commit()

    # core field change forbidden
    ctx.context_type = DecisionContextType.IC_MEETING
    with pytest.raises(DecisionContextMutationError):
        db_session.flush()

