"""add candidate profile fields

Revision ID: a7c308c97029
Revises: 9376c3b92e7b
Create Date: 2025-08-10

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a7c308c97029'
down_revision = '9376c3b92e7b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('candidates') as batch:
        batch.add_column(sa.Column('birthdate', sa.Date(), nullable=True))
        batch.add_column(sa.Column('applied_at', sa.DateTime(), nullable=True))
        batch.add_column(sa.Column('qualifications', sa.Text(), nullable=True))
        batch.add_column(sa.Column('skills', sa.Text(), nullable=True))
        batch.add_column(sa.Column('languages', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('candidates') as batch:
        batch.drop_column('languages')
        batch.drop_column('skills')
        batch.drop_column('qualifications')
        batch.drop_column('applied_at')
        batch.drop_column('birthdate')
