"""add_narrative_analysis_to_enrichment

Revision ID: 20260204_add_narrative_analysis
Revises: 2dc4e419b242
Create Date: 2026-02-04 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260204_add_narrative_analysis'
down_revision = '2dc4e419b242'
branch_labels = None
depends_on = None


def upgrade():
    # Add narrative_analysis JSONB column to information_event_enrichment
    op.add_column('information_event_enrichment', sa.Column('narrative_analysis', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Detailed AI analysis (expectation gap, trapped persona, etc)'))
    op.create_index(op.f('ix_enrichment_narrative_analysis'), 'information_event_enrichment', ['narrative_analysis'], unique=False, postgresql_using='gin')


def downgrade():
    op.drop_index(op.f('ix_enrichment_narrative_analysis'), table_name='information_event_enrichment', postgresql_using='gin')
    op.drop_column('information_event_enrichment', 'narrative_analysis')
