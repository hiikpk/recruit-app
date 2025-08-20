"""drop candidate_id from interviews

Revision ID: 4e4fdae6d259
Revises: 6413a7976520
Create Date: 2025-08-10
"""

from alembic import op
import sqlalchemy as sa

revision = '4e4fdae6d259'
down_revision = '6413a7976520'
branch_labels = None
depends_on = None


def upgrade():
	with op.batch_alter_table('interviews') as batch_op:
		try:
			batch_op.drop_column('candidate_id')
		except Exception:
			pass


def downgrade():
	with op.batch_alter_table('interviews') as batch_op:
		batch_op.add_column(sa.Column('candidate_id', sa.Integer(), nullable=True))
