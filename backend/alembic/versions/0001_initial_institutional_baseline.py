"""Initial institutional baseline for decision risk infrastructure."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# Revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # Explicit PostgreSQL ENUM types (created once, reused across tables).
    # NOTE: Some types are duplicated to preserve compatibility with existing
    # ORM enum naming while also creating the required *_enum types.
    # -------------------------------------------------------------------------
    decision_risk_type_enum = postgresql.ENUM(
        "TIMING_DISTORTION",
        "NARRATIVE_CONTAMINATION",
        "CONSENSUS_TRAP",
        "STRUCTURAL_DECISION_RISK",
        name="decision_risk_type_enum",
        create_type=False,
    )
    recommended_posture_enum = postgresql.ENUM(
        "IGNORE",
        "REVIEW",
        "DELAY",
        name="recommended_posture_enum",
        create_type=False,
    )
    narrative_status_enum = postgresql.ENUM(
        "ACTIVE",
        "FADING",
        "DORMANT",
        name="narrative_status_enum",
        create_type=False,
    )
    distortion_type_enum = postgresql.ENUM(
        "LATE_ACTION",
        "PREMATURE_ACTION",
        name="distortion_type_enum",
        create_type=False,
    )
    decision_context_type_enum = postgresql.ENUM(
        "IC_MEETING",
        "PM_REVIEW",
        "ALLOCATION_DECISION",
        "STRATEGY_REVIEW",
        name="decision_context_type_enum",
        create_type=False,
    )
    environment_state_enum = postgresql.ENUM(
        "CLEAN",
        "CAUTION",
        "CONTAMINATED",
        name="environment_state_enum",
        create_type=False,
    )

    # ORM enum type names currently used by models (compatibility types).
    decision_risk_type = postgresql.ENUM(
        "TIMING_DISTORTION",
        "NARRATIVE_CONTAMINATION",
        "CONSENSUS_TRAP",
        "STRUCTURAL_DECISION_RISK",
        name="decision_risk_type",
        create_type=False,
    )
    decision_recommended_posture = postgresql.ENUM(
        "IGNORE",
        "REVIEW",
        "DELAY",
        name="decision_recommended_posture",
        create_type=False,
    )
    narrative_status = postgresql.ENUM(
        "ACTIVE",
        "FADING",
        "DORMANT",
        name="narrative_status",
        create_type=False,
    )
    timing_distortion_type = postgresql.ENUM(
        "LATE_ACTION",
        "PREMATURE_ACTION",
        name="timing_distortion_type",
        create_type=False,
    )
    decision_context_type = postgresql.ENUM(
        "IC_MEETING",
        "PM_REVIEW",
        "ALLOCATION_DECISION",
        "STRATEGY_REVIEW",
        name="decision_context_type",
        create_type=False,
    )
    decision_environment_state = postgresql.ENUM(
        "CLEAN",
        "CAUTION",
        "CONTAMINATED",
        name="decision_environment_state",
        create_type=False,
    )

    bind = op.get_bind()
    for enum_type in (
        decision_risk_type_enum,
        recommended_posture_enum,
        narrative_status_enum,
        distortion_type_enum,
        decision_context_type_enum,
        environment_state_enum,
        decision_risk_type,
        decision_recommended_posture,
        narrative_status,
        timing_distortion_type,
        decision_context_type,
        decision_environment_state,
    ):
        enum_type.create(bind, checkfirst=True)

    # -------------------------------------------------------------------------
    # 1. information_events
    # -------------------------------------------------------------------------
    op.create_table(
        "information_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column("external_ref", sa.Text(), nullable=True),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body_excerpt", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("content_hash_sha256", sa.LargeBinary(length=32), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "octet_length(content_hash_sha256) = 32",
            name="ck_information_events_sha256_len",
        ),
    )
    op.create_index(
        "ix_information_events_observed_at",
        "information_events",
        ["observed_at"],
        unique=False,
    )
    op.create_index(
        "ix_information_events_source_ref_observed_at",
        "information_events",
        ["source_ref", "observed_at"],
        unique=False,
    )
    op.create_index(
        "ux_information_events_source_ref_external_ref",
        "information_events",
        ["source_ref", "external_ref"],
        unique=True,
        postgresql_where=sa.text("external_ref IS NOT NULL"),
    )
    op.create_index(
        "ux_information_events_source_ref_canonical_url",
        "information_events",
        ["source_ref", "canonical_url"],
        unique=True,
        postgresql_where=sa.text("canonical_url IS NOT NULL"),
    )

    # -------------------------------------------------------------------------
    # 2. decision_risk_events
    # -------------------------------------------------------------------------
    op.create_table(
        "decision_risk_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "information_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "information_events.id",
                name="fk_decision_risk_events_information_event_id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column("risk_type", decision_risk_type, nullable=False),
        sa.Column("severity", sa.SmallInteger(), nullable=False),
        sa.Column("affected_decisions", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("recommended_posture", decision_recommended_posture, nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "severity >= 1 AND severity <= 5",
            name="ck_decision_risk_events_severity_range",
        ),
        sa.CheckConstraint(
            "(valid_to IS NULL) OR (valid_to > valid_from)",
            name="ck_decision_risk_events_valid_to_after_valid_from",
        ),
    )
    op.create_index(
        "ix_decision_risk_events_information_event_id",
        "decision_risk_events",
        ["information_event_id"],
        unique=False,
    )
    op.create_index(
        "ix_decision_risk_events_valid_range",
        "decision_risk_events",
        ["valid_from", "valid_to"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # 3. narrative_clusters
    # -------------------------------------------------------------------------
    op.create_table(
        "narrative_clusters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("theme", sa.Text(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("saturation_level", sa.SmallInteger(), nullable=False),
        sa.Column("status", narrative_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "saturation_level >= 1 AND saturation_level <= 5",
            name="ck_narrative_clusters_saturation_range",
        ),
    )
    op.create_index(
        "ix_narrative_clusters_status",
        "narrative_clusters",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_narrative_clusters_last_seen_at",
        "narrative_clusters",
        ["last_seen_at"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # 4. narrative_memberships (association table)
    # -------------------------------------------------------------------------
    op.create_table(
        "narrative_memberships",
        sa.Column(
            "narrative_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "narrative_clusters.id",
                name="fk_narrative_memberships_narrative_id",
                ondelete="RESTRICT",
            ),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "decision_risk_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "decision_risk_events.id",
                name="fk_narrative_memberships_decision_risk_event_id",
                ondelete="RESTRICT",
            ),
            primary_key=True,
            nullable=False,
        ),
    )

    # -------------------------------------------------------------------------
    # 5. consensus_pressure_events
    # -------------------------------------------------------------------------
    op.create_table(
        "consensus_pressure_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "narrative_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "narrative_clusters.id",
                name="fk_consensus_pressure_events_narrative_id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column("pressure_level", sa.SmallInteger(), nullable=False),
        sa.Column("dominant_sources", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "pressure_level >= 1 AND pressure_level <= 5",
            name="ck_consensus_pressure_events_pressure_range",
        ),
    )
    op.create_index(
        "ix_consensus_pressure_events_narrative_id",
        "consensus_pressure_events",
        ["narrative_id"],
        unique=False,
    )
    op.create_index(
        "ix_consensus_pressure_events_detected_at",
        "consensus_pressure_events",
        ["detected_at"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # 6. timing_distortion_windows
    # -------------------------------------------------------------------------
    op.create_table(
        "timing_distortion_windows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "decision_risk_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "decision_risk_events.id",
                name="fk_timing_distortion_windows_decision_risk_event_id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("distortion_type", timing_distortion_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "window_end > window_start",
            name="ck_timing_distortion_windows_end_after_start",
        ),
    )
    op.create_index(
        "ix_timing_distortion_windows_decision_risk_event_id",
        "timing_distortion_windows",
        ["decision_risk_event_id"],
        unique=False,
    )
    op.create_index(
        "ix_timing_distortion_windows_range",
        "timing_distortion_windows",
        ["window_start", "window_end"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # 7. decision_contexts
    # -------------------------------------------------------------------------
    op.create_table(
        "decision_contexts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("context_type", decision_context_type, nullable=False),
        sa.Column("context_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_decision_contexts_context_time",
        "decision_contexts",
        ["context_time"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # 8. decision_environment_snapshots
    # -------------------------------------------------------------------------
    op.create_table(
        "decision_environment_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("snapshot_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("environment_state", decision_environment_state, nullable=False),
        sa.Column("dominant_risks", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("risk_density", sa.SmallInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "risk_density >= 0",
            name="ck_decision_environment_snapshots_risk_density_nonneg",
        ),
    )
    op.create_index(
        "ix_decision_environment_snapshots_snapshot_time",
        "decision_environment_snapshots",
        ["snapshot_time"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # 9. decision_impact_records
    # -------------------------------------------------------------------------
    op.create_table(
        "decision_impact_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "decision_context_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "decision_contexts.id",
                name="fk_decision_impact_records_decision_context_id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "environment_snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "decision_environment_snapshots.id",
                name="fk_decision_impact_records_environment_snapshot_id",
                ondelete="RESTRICT",
            ),
            nullable=True,
        ),
        sa.Column("qualitative_outcome", sa.Text(), nullable=False),
        sa.Column("learning_flags", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_decision_impact_records_decision_context_id",
        "decision_impact_records",
        ["decision_context_id"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # 10. re_evaluation_logs
    # -------------------------------------------------------------------------
    op.create_table(
        "re_evaluation_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("new_state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("re_evaluated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_re_evaluation_logs_entity",
        "re_evaluation_logs",
        ["entity_type", "entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_re_evaluation_logs_re_evaluated_at",
        "re_evaluation_logs",
        ["re_evaluated_at"],
        unique=False,
    )


def downgrade() -> None:
    # Drop tables in strict reverse dependency order.
    op.drop_index("ix_re_evaluation_logs_re_evaluated_at", table_name="re_evaluation_logs")
    op.drop_index("ix_re_evaluation_logs_entity", table_name="re_evaluation_logs")
    op.drop_table("re_evaluation_logs")

    op.drop_index("ix_decision_impact_records_decision_context_id", table_name="decision_impact_records")
    op.drop_table("decision_impact_records")

    op.drop_index(
        "ix_decision_environment_snapshots_snapshot_time", table_name="decision_environment_snapshots"
    )
    op.drop_table("decision_environment_snapshots")

    op.drop_index("ix_decision_contexts_context_time", table_name="decision_contexts")
    op.drop_table("decision_contexts")

    op.drop_index("ix_timing_distortion_windows_range", table_name="timing_distortion_windows")
    op.drop_index(
        "ix_timing_distortion_windows_decision_risk_event_id",
        table_name="timing_distortion_windows",
    )
    op.drop_table("timing_distortion_windows")

    op.drop_index("ix_consensus_pressure_events_detected_at", table_name="consensus_pressure_events")
    op.drop_index("ix_consensus_pressure_events_narrative_id", table_name="consensus_pressure_events")
    op.drop_table("consensus_pressure_events")

    op.drop_table("narrative_memberships")

    op.drop_index("ix_narrative_clusters_last_seen_at", table_name="narrative_clusters")
    op.drop_index("ix_narrative_clusters_status", table_name="narrative_clusters")
    op.drop_table("narrative_clusters")

    op.drop_index("ix_decision_risk_events_valid_range", table_name="decision_risk_events")
    op.drop_index(
        "ix_decision_risk_events_information_event_id", table_name="decision_risk_events"
    )
    op.drop_table("decision_risk_events")

    op.drop_index(
        "ux_information_events_source_ref_canonical_url", table_name="information_events"
    )
    op.drop_index(
        "ux_information_events_source_ref_external_ref", table_name="information_events"
    )
    op.drop_index(
        "ix_information_events_source_ref_observed_at", table_name="information_events"
    )
    op.drop_index("ix_information_events_observed_at", table_name="information_events")
    op.drop_table("information_events")

    # Drop ENUM types last.
    bind = op.get_bind()
    for enum_name in (
        "decision_environment_state",
        "decision_context_type",
        "timing_distortion_type",
        "narrative_status",
        "decision_recommended_posture",
        "decision_risk_type",
        "environment_state_enum",
        "decision_context_type_enum",
        "distortion_type_enum",
        "narrative_status_enum",
        "recommended_posture_enum",
        "decision_risk_type_enum",
    ):
        postgresql.ENUM(name=enum_name).drop(bind, checkfirst=True)

