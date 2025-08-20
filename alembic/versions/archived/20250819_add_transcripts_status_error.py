"""add transcripts status and error

Revision ID: 20250819_add_transcripts_status_error
Revises: 20250817_add_transcripts_utterances_metrics
Create Date: 2025-08-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20250819_add_transcripts_status_error'
down_revision = '20250817_add_transcripts_utterances_metrics'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    insp = inspect(conn)
    if insp.has_table('transcripts'):
        cols = [c['name'] for c in insp.get_columns('transcripts')]
        if 'status' not in cols:
            op.add_column('transcripts', sa.Column('status', sa.String(length=20), server_default='pending', nullable=True))
        if 'error' not in cols:
            op.add_column('transcripts', sa.Column('error', sa.Text(), nullable=True))


def downgrade():
    conn = op.get_bind()
    insp = inspect(conn)
    if insp.has_table('transcripts'):
        cols = [c['name'] for c in insp.get_columns('transcripts')]
        if 'error' in cols:
            op.drop_column('transcripts', 'error')
        if 'status' in cols:
            op.drop_column('transcripts', 'status')
