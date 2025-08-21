"""Add interviews.scheduled_at (placeholder)

This is a safe idempotent placeholder to satisfy environments that reference
the revision id `20250820_add_interviews_scheduled_at`. It will add the
`scheduled_at` column if missing. Non-destructive when column already exists.

Revision ID: 20250820_add_interviews_scheduled_at
Revises: 
Create Date: 2025-08-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '20250820_add_interviews_scheduled_at'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    cols = [c['name'] for c in inspector.get_columns('interviews')]
    if 'scheduled_at' not in cols:
        with op.batch_alter_table('interviews') as batch_op:
            batch_op.add_column(sa.Column('scheduled_at', sa.DateTime(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    cols = [c['name'] for c in inspector.get_columns('interviews')]
    if 'scheduled_at' in cols:
        with op.batch_alter_table('interviews') as batch_op:
            batch_op.drop_column('scheduled_at')
