"""add content fields to information_events

Revision ID: 20260201_add_content_fields
Revises: 
Create Date: 2026-02-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260201_add_content_fields'
down_revision = '083533b83583'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('information_events', sa.Column('content_html', sa.Text(), nullable=True))
    op.add_column('information_events', sa.Column('content_text', sa.Text(), nullable=True))
    op.add_column('information_events', sa.Column('content_excerpt', sa.Text(), nullable=True))
    op.add_column('information_events', sa.Column('fetched_content_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('information_events', sa.Column('content_fetch_status', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('information_events', 'content_fetch_status')
    op.drop_column('information_events', 'fetched_content_at')
    op.drop_column('information_events', 'content_excerpt')
    op.drop_column('information_events', 'content_text')
    op.drop_column('information_events', 'content_html')
