"""merge heads 20250820

Revision ID: m20250820a001
Revises: 20250820_add_scheduled_at_to_interviews,83ff2ec11d22
Create Date: 2025-08-20 20:20:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "m20250820a001"
down_revision = ("20250820_add_scheduled_at_to_interviews", "83ff2ec11d22")
branch_labels = None
depends_on = None


def upgrade():
    # no-op merge
    pass


def downgrade():
    # no-op
    pass
