"""add interview step

Revision ID: 6413a7976520
Revises: c7b6d82d0af9
Create Date: 2025-08-10
"""

from alembic import op
import sqlalchemy as sa

revision = '6413a7976520'
down_revision = 'c7b6d82d0af9'
branch_labels = None
depends_on = None


def upgrade():
	with op.batch_alter_table('interviews') as batch_op:
		batch_op.add_column(sa.Column('step', sa.String(length=20), nullable=True))


def downgrade():
	with op.batch_alter_table('interviews') as batch_op:
		batch_op.drop_column('step')
