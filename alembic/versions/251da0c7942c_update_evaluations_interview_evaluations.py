"""update evaluations -> interview_evaluations and reshape columns

Revision ID: 251da0c7942c
Revises: 4e4fdae6d259
Create Date: 2025-08-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import NoSuchTableError

revision = "251da0c7942c"
down_revision = "4e4fdae6d259"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # --- Ensure the target table exists (empty-DB friendly) ---
    # If neither the new table nor the old one exists, create a minimal target table.
    if not has_table(insp, "interview_evaluations") and not has_table(insp, "evaluations"):
        op.create_table(
            "interview_evaluations",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("created_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
        )

    # If the old table exists and the new one doesn't, rename it first.
    if has_table(insp, "evaluations") and not has_table(insp, "interview_evaluations"):
        op.rename_table("evaluations", "interview_evaluations")

    # At this point, the target table should exist. Proceed defensively.
    if not has_table(insp, "interview_evaluations"):
        # Safety net: create minimal table if rename above didn't run for some reason
        op.create_table(
            "interview_evaluations",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("created_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
        )

    # Refresh inspector cache if needed
    insp = sa.inspect(bind)

    # --- Shape columns to the new schema ---
    with op.batch_alter_table("interview_evaluations") as b:
        # Drop legacy columns if present
        if has_column(insp, "interview_evaluations", "application_id"):
            b.drop_column("application_id")
        if has_column(insp, "interview_evaluations", "interviewer_id"):
            b.drop_column("interviewer_id")
        if has_column(insp, "interview_evaluations", "rubric_json"):
            b.drop_column("rubric_json")
        if has_column(insp, "interview_evaluations", "score_total"):
            b.drop_column("score_total")
        if has_column(insp, "interview_evaluations", "decision"):
            b.drop_column("decision")

        # Add required/new columns (FK will be created via batch_op)
        if not has_column(insp, "interview_evaluations", "interview_id"):
            b.add_column(sa.Column("interview_id", sa.Integer(), nullable=True))
            b.create_foreign_key(
                "fk_interview_evaluations_interview_id",
                referent_table="interviews",
                local_cols=["interview_id"],
                remote_cols=["id"],
            )

        for col, type_ in [
            ("overall_score", sa.Numeric(5, 2)),
            ("speaking", sa.Numeric(5, 2)),
            ("logical", sa.Numeric(5, 2)),
            ("volume", sa.Numeric(5, 2)),
            ("honesty", sa.Numeric(5, 2)),
            ("proactive", sa.Numeric(5, 2)),
            ("raw_metrics", sa.JSON()),
            ("audio_file_id", sa.Integer()),
        ]:
            if not has_column(insp, "interview_evaluations", col):
                b.add_column(sa.Column(col, type_))

        if not has_column(insp, "interview_evaluations", "created_at"):
            b.add_column(sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False))

def downgrade():
    # 破壊的変更のため簡易ダウングレードのみ
    pass



def has_table(insp: sa.engine.reflection.Inspector, table: str) -> bool:
    try:
        return insp.has_table(table)
    except Exception:
        return False


def has_column(insp: sa.engine.reflection.Inspector, table: str, column: str) -> bool:
    try:
        return column in {c["name"] for c in insp.get_columns(table)}
    except NoSuchTableError:
        return False