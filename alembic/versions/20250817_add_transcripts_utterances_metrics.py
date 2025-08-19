"""add transcripts utterances and metrics

Revision ID: 20250817_add_transcripts_utterances_metrics
Revises: 70fd5ab9e65b
Create Date: 2025-08-17 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '20250817_add_transcripts_utterances_metrics'
down_revision = '70fd5ab9e65b'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table('transcripts'):
        cols = [c['name'] for c in insp.get_columns('transcripts')]
    else:
        cols = []
    if 'utterances' not in cols:
        op.add_column('transcripts', sa.Column('utterances', sa.JSON(), nullable=True))
    if 'metrics' not in cols:
        op.add_column('transcripts', sa.Column('metrics', sa.JSON(), nullable=True))


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table('transcripts'):
        cols = [c['name'] for c in insp.get_columns('transcripts')]
        if 'metrics' in cols:
            op.drop_column('transcripts', 'metrics')
        if 'utterances' in cols:
            op.drop_column('transcripts', 'utterances')
