"""merge heads: 20250818_add_files_candidate_id + 20250819_add_transcripts_status_error

Revision ID: m20250819a001
Revises: 20250818_add_files_candidate_id, 20250819_add_transcripts_status_error
Create Date: 2025-08-19 00:10:00.000000

This is a no-op merge revision to unify heads so migrations can be applied safely.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "m20250819a001"
down_revision = ("20250818_add_files_candidate_id", "20250819_add_transcripts_status_error")
branch_labels = None
depends_on = None


def upgrade():
    # no-op merge
    pass


def downgrade():
    # no-op
    pass
