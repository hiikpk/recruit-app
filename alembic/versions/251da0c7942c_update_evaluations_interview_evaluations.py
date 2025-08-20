"""update evaluations -> interview_evaluations and reshape columns

Revision ID: 251da0c7942c
Revises: 4e4fdae6d259
Create Date: 2025-08-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy import exc as sa_exc

revision = "251da0c7942c"
down_revision = "4e4fdae6d259"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Use get_table_names() for stable existence checks (search_path-aware)
    tables = set(insp.get_table_names())

    # 1) If old name exists and new one doesn't, rename first
    if "interview_evaluations" not in tables and "evaluations" in tables:
        op.rename_table("evaluations", "interview_evaluations")
        # refresh inspector
        insp = sa.inspect(bind)
        tables = set(insp.get_table_names())

    # 2) If neither exists, create a minimal new table (guarded against duplicates)
    if "interview_evaluations" not in tables and "evaluations" not in tables:
        try:
            op.create_table(
                "interview_evaluations",
                sa.Column("id", sa.Integer, primary_key=True),
                sa.Column("created_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
                sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
            )
        except sa_exc.ProgrammingError:
            # In case of a race/duplicate, continue defensively
            pass
        # refresh inspector again
        insp = sa.inspect(bind)
        tables = set(insp.get_table_names())

    # 3) Shape columns only if target table exists
    if "interview_evaluations" in tables:
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

            # Add required/new columns
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
        return table in set(insp.get_table_names())
    except Exception:
        return False


def has_column(insp: sa.engine.reflection.Inspector, table: str, column: str) -> bool:
    try:
        return column in {c["name"] for c in insp.get_columns(table)}
    except NoSuchTableError:
        return False