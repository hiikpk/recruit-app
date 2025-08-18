"""add interview step

Revision ID: 6413a7976520
Revises: c7b6d82d0af9
Create Date: 2025-08-10
"""

from alembic import op
import sqlalchemy as sa

revision = "6413a7976520"
down_revision = "c7b6d82d0af9"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("interviews")}

    with op.batch_alter_table("interviews") as batch:
        if "step" not in cols:
            batch.add_column(sa.Column("step", sa.String(length=20), nullable=True))


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("interviews")}

    with op.batch_alter_table("interviews") as batch:
        if "step" in cols:
            batch.drop_column("step")