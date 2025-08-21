"""Merge 0001_initial and 20250820_add_interviews_scheduled_at

Revision ID: m20250821a001
Revises: 0001_initial, 20250820_add_interviews_scheduled_at
Create Date: 2025-08-21 00:00:00.000000
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'm20250821a001'
down_revision = ('0001_initial', '20250820_add_interviews_scheduled_at')
branch_labels = None
depends_on = None


def upgrade():
    # merge point: no operations
    pass


def downgrade():
    # noop
    pass
