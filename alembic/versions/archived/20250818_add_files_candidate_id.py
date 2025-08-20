"""add candidate_id to files

Revision ID: 20250818_add_files_candidate_id
Revises: 20250818_add_user_tz_offset
Create Date: 2025-08-18 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250818_add_files_candidate_id'
down_revision = '20250818_add_user_tz_offset'
branch_labels = None
depends_on = None


def upgrade():
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('files', schema=None) as batch_op:
        batch_op.add_column(sa.Column('candidate_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_files_candidate', 'candidates', ['candidate_id'], ['id'])


def downgrade():
    with op.batch_alter_table('files', schema=None) as batch_op:
        batch_op.drop_constraint('fk_files_candidate', type_='foreignkey')
        batch_op.drop_column('candidate_id')
