"""update evaluations -> interview_evaluations and reshape columns

Revision ID: 251da0c7942c
Revises: 4e4fdae6d259
Create Date: 2025-08-14
"""
from alembic import op
import sqlalchemy as sa

revision = "251da0c7942c"
down_revision = "4e4fdae6d259"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    # テーブル名を揃える（evaluations -> interview_evaluations）
    if "interview_evaluations" not in tables and "evaluations" in tables:
        op.rename_table("evaluations", "interview_evaluations")

# ...existing code...
    # 形に合わせて列を整理
    with op.batch_alter_table("interview_evaluations") as b:
        # 旧列の削除
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

        # 必須/新規列の追加（FK は別操作で付与）
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
            b.add_column(sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))
# ...existing code...

def downgrade():
    # 破壊的変更のため簡易ダウングレードのみ
    pass


def has_column(insp: sa.engine.reflection.Inspector, table: str, column: str) -> bool:
    return column in [c["name"] for c in insp.get_columns(table)]