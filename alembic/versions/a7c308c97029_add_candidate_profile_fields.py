"""add candidate profile fields

Revision ID: a7c308c97029
Revises: bb6d1452684e
Create Date: 2025-08-10

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a7c308c97029'
down_revision = 'bb6d1452684e'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("candidates")}

    with op.batch_alter_table('candidates') as batch:
        if "birthdate" not in cols:
            batch.add_column(sa.Column('birthdate', sa.Date(), nullable=True))
        if "applied_at" not in cols:
            batch.add_column(sa.Column('applied_at', sa.Date(), nullable=True))
        if "qualifications" not in cols:
            batch.add_column(sa.Column('qualifications', sa.Text(), nullable=True))
        if "skills" not in cols:
            batch.add_column(sa.Column('skills', sa.Text(), nullable=True))
        if "languages" not in cols:
            batch.add_column(sa.Column('languages', sa.Text(), nullable=True))


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("candidates")}

    with op.batch_alter_table('candidates') as batch:
        if "languages" in cols:
            batch.drop_column('languages')
        if "skills" in cols:
            batch.drop_column('skills')
        if "qualifications" in cols:
            batch.drop_column('qualifications')
        if "applied_at" in cols:
            batch.drop_column('applied_at')
        if "birthdate" in cols:
            batch.drop_column('birthdate')