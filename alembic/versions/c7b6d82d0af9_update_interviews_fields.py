"""update interviews fields

Revision ID: c7b6d82d0af9
Revises: a7c308c97029
Create Date: 2025-08-10
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c7b6d82d0af9'
down_revision = 'a7c308c97029'
branch_labels = None
depends_on = None


def upgrade():
	with op.batch_alter_table('interviews') as batch_op:
		# drop old end time
		try:
			batch_op.drop_column('scheduled_end')
		except Exception:
			pass
		# add new columns
		batch_op.add_column(sa.Column('candidate_id', sa.Integer(), nullable=True))
		batch_op.add_column(sa.Column('rank', sa.String(length=2), nullable=True))
		batch_op.add_column(sa.Column('decision', sa.String(length=20), nullable=True))
		batch_op.add_column(sa.Column('comment', sa.Text(), nullable=True))
		batch_op.add_column(sa.Column('interviewer', sa.String(length=120), nullable=True))


def downgrade():
	with op.batch_alter_table('interviews') as batch_op:
		batch_op.drop_column('interviewer')
		batch_op.drop_column('comment')
		batch_op.drop_column('decision')
		batch_op.drop_column('rank')
		batch_op.drop_column('candidate_id')
		batch_op.add_column(sa.Column('scheduled_end', sa.DateTime(), nullable=True))
