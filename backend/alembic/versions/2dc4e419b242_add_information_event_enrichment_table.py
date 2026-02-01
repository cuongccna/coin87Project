"""add_information_event_enrichment_table

Revision ID: 2dc4e419b242
Revises: 20260201_add_content_fields
Create Date: 2026-02-01 23:08:07.313197

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2dc4e419b242'
down_revision = '20260201_add_content_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create information_event_enrichment table
    op.create_table(
        'information_event_enrichment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('information_event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ai_summary', sa.String(length=500), nullable=True, comment='AI-generated summary (max 500 chars)'),
        sa.Column('entities', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Extracted entities (tokens, protocols, people, orgs)'),
        sa.Column('sentiment', sa.String(length=20), nullable=True, comment='bullish|bearish|neutral'),
        sa.Column('confidence', sa.Float(), nullable=True, comment='AI confidence score 0.0-1.0'),
        sa.Column('keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Extracted keywords'),
        sa.Column('category', sa.String(length=50), nullable=True, comment='Content category: regulation|technology|market|security|other'),
        sa.Column('worth_click_score', sa.Float(), nullable=True, comment='Score from worth-click scorer (0-10)'),
        sa.Column('worth_click_breakdown', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Scoring breakdown details'),
        sa.Column('filter_decision', sa.String(length=50), nullable=True, comment='Pre-filter decision: pass|reject_*'),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['information_event_id'],
            ['information_events.id'],
            name='fk_enrichment_information_event',
            ondelete='CASCADE'
        ),
        comment='AI-enriched analysis for InformationEvents (derived data, separate from immutable raw input)'
    )
    
    # Indexes for common queries
    op.create_index('idx_enrichment_event_id', 'information_event_enrichment', ['information_event_id'])
    op.create_index('idx_enrichment_sentiment', 'information_event_enrichment', ['sentiment'])
    op.create_index('idx_enrichment_category', 'information_event_enrichment', ['category'])
    op.create_index('idx_enrichment_score', 'information_event_enrichment', ['worth_click_score'])
    op.create_index('idx_enrichment_generated_at', 'information_event_enrichment', ['generated_at'])
    
    # Unique constraint: one enrichment per event
    op.create_unique_constraint('uq_enrichment_event', 'information_event_enrichment', ['information_event_id'])


def downgrade() -> None:
    op.drop_table('information_event_enrichment')
