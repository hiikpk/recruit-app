"""add transcripts utterances and metrics

Revision ID: 20250817_add_transcripts_utterances_metrics
Revises: 70fd5ab9e65b
Create Date: 2025-08-17 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '20250817_add_transcripts_utterances_metrics'
down_revision = '70fd5ab9e65b'
branch_labels = None
depends_on = None


def has_table(insp, name: str) -> bool:
    try:
        return name in set(insp.get_table_names())
    except Exception:
        return False

def has_column(insp, table: str, column: str) -> bool:
    try:
        return column in {c["name"] for c in insp.get_columns(table)}
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not has_table(insp, "transcripts"):
        op.create_table(
            "transcripts",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("created_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
        )
        insp = sa.inspect(bind)

    with op.batch_alter_table("transcripts") as b:
        if not has_column(insp, "transcripts", "utterances"):
            b.add_column(sa.Column("utterances", sa.JSON(), nullable=True))
        if not has_column(insp, "transcripts", "metrics"):
            b.add_column(sa.Column("metrics", sa.JSON(), nullable=True))


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if has_table(insp, "transcripts"):
        with op.batch_alter_table("transcripts") as b:
            if has_column(insp, "transcripts", "metrics"):
                b.drop_column("metrics")
            if has_column(insp, "transcripts", "utterances"):
                b.drop_column("utterances")
