"""add user tz offset

Revision ID: 20250818_add_user_tz_offset
Revises: m20250818a001
Create Date: 2025-08-18 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250818_add_user_tz_offset'
down_revision = 'm20250818a001'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('tz_offset_minutes', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('users', 'tz_offset_minutes')
