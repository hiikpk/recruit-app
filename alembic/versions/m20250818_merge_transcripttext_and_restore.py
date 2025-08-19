"""merge heads: 20250818_add_interview_transcript_text + 9c06b53f0fd3

Revision ID: m20250818a001
Revises: 20250818_add_interview_transcript_text, 9c06b53f0fd3
Create Date: 2025-08-18 00:10:00.000000

This is a no-op merge revision to unify heads so migrations can be applied safely.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "m20250818a001"
down_revision = ("20250818_add_interview_transcript_text", "9c06b53f0fd3")
branch_labels = None
depends_on = None


def upgrade():
    # no-op merge
    pass


def downgrade():
    # no-op
    pass
