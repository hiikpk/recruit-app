"""add transcript_text to interviews

Revision ID: 20250818_add_interview_transcript_text
Revises: 
Create Date: 2025-08-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250818_add_interview_transcript_text'
down_revision = '20250817_add_settings_table'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('interviews', sa.Column('transcript_text', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('interviews', 'transcript_text')
