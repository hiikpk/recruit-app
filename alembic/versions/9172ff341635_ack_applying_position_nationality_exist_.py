"""ack: applying_position & nationality exist on candidates

Revision ID: 9172ff341635
Revises: 251da0c7942c
Create Date: 2025-08-15
"""

from alembic import op
import sqlalchemy as sa

# Alembic identifiers
revision = "9172ff341635"
down_revision = "251da0c7942c"
branch_labels = None
depends_on = None


def upgrade():
    """No-op if columns already exist; create if missing."""
    bind = op.get_bind()
    insp = sa.inspect(bind)

    cols = {c["name"] for c in insp.get_columns("candidates")}
    with op.batch_alter_table("candidates") as batch:
        if "applying_position" not in cols:
            batch.add_column(sa.Column("applying_position", sa.String(length=100), nullable=True))
        if "nationality" not in cols:
            batch.add_column(sa.Column("nationality", sa.String(length=100), nullable=True))

    # index (create only if absent and column present)
    idx_names = {i["name"] for i in insp.get_indexes("candidates")}
    cols = {c["name"] for c in insp.get_columns("candidates")}  # refresh
    if "applying_position" in cols and "ix_candidates_applying_position" not in idx_names:
        op.create_index("ix_candidates_applying_position", "candidates", ["applying_position"])


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    idx_names = {i["name"] for i in insp.get_indexes("candidates")}
    if "ix_candidates_applying_position" in idx_names:
        op.drop_index("ix_candidates_applying_position", table_name="candidates")

    cols = {c["name"] for c in insp.get_columns("candidates")}
    with op.batch_alter_table("candidates") as batch:
        if "nationality" in cols:
            batch.drop_column("nationality")
        if "applying_position" in cols:
            batch.drop_column("applying_position")