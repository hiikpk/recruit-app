from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine import reflection

# revision identifiers, used by Alembic.
revision = "00a330981fad"        # 自動生成された値のままでOK（ここはそのままにする）
down_revision = "add_missing_candidates_cols_20250820"   # 自動生成された値のままでOK
branch_labels = None
depends_on = None


def _has_table(conn, name: str) -> bool:
    insp = reflection.Inspector.from_engine(conn)
    return insp.has_table(name)


def _has_col(conn, table: str, col: str) -> bool:
    insp = reflection.Inspector.from_engine(conn)
    return any(c["name"] == col for c in insp.get_columns(table))


def upgrade():
    conn = op.get_bind()

    # organizations が無い環境でも落ちないように最小限で用意（既にあればスキップ）
    if not _has_table(conn, "organizations"):
        op.create_table(
            "organizations",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
        )

    # candidates テーブルの存在を保証（最低限の骨組み）
    if not _has_table(conn, "candidates"):
        op.create_table(
            "candidates",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("created_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
        )

    # org_id カラム（ダッシュボードのWHEREで使用）
    if not _has_col(conn, "candidates", "org_id"):
        op.add_column("candidates", sa.Column("org_id", sa.Integer(), nullable=True))
        # FK は organizations がある場合のみ（無い環境だと失敗するので存在チェック）
        if _has_table(conn, "organizations"):
            op.create_foreign_key(
                "fk_candidates_org_id_organizations",
                "candidates",
                "organizations",
                ["org_id"],
                ["id"],
                ondelete="SET NULL",
            )
        op.create_index("ix_candidates_org_id", "candidates", ["org_id"])

    # memo カラム（一覧SELECTで使用）
    if not _has_col(conn, "candidates", "memo"):
        op.add_column("candidates", sa.Column("memo", sa.Text(), nullable=True))


def downgrade():
    conn = op.get_bind()
    # なるべく安全にロールバック
    if _has_table(conn, "candidates"):
        try:
            op.drop_constraint("fk_candidates_org_id_organizations", "candidates", type_="foreignkey")
        except Exception:
            pass
        try:
            op.drop_index("ix_candidates_org_id", table_name="candidates")
        except Exception:
            pass
        if _has_col(conn, "candidates", "org_id"):
            op.drop_column("candidates", "org_id")
        if _has_col(conn, "candidates", "memo"):
            op.drop_column("candidates", "memo")