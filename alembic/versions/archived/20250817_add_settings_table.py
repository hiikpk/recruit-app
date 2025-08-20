"""add settings table

Revision ID: 20250817_add_settings_table
Revises: 20250817_add_transcripts_utterances_metrics
Create Date: 2025-08-17 00:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '20250817_add_settings_table'
down_revision = '20250817_add_transcripts_utterances_metrics'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table('settings'):
        op.create_table(
            'settings',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('org_id', sa.Integer, nullable=False, index=True),
            sa.Column('key', sa.String(128), nullable=False),
            sa.Column('value', sa.Text, nullable=True),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
            sa.UniqueConstraint('org_id', 'key', name='uq_settings_org_key')
        )


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table('settings'):
        op.drop_table('settings')
