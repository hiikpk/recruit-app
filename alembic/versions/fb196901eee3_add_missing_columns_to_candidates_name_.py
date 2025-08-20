from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine import reflection

# revision identifiers, used by Alembic.
revision = "add_missing_candidates_cols_20250820"
down_revision = "20250820_create_orgs"
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

    if not _has_table(conn, "candidates"):
        # もし環境によって candidates 自体が未作成なら最低限の土台を作る
        op.create_table(
            "candidates",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("org_id", sa.Integer, nullable=True),
            sa.Column("created_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
        )

    # name（一覧で使用）
    if not _has_col(conn, "candidates", "name"):
        op.add_column("candidates", sa.Column("name", sa.String(255), nullable=True))

    # channel（ダッシュボード集計で使用）
    if not _has_col(conn, "candidates", "channel"):
        op.add_column("candidates", sa.Column("channel", sa.String(100), nullable=True))

    # 参考：他の画面で参照している可能性が高い主要カラム
    maybe_cols = [
        ("name_yomi", sa.String(255)),
        ("email", sa.String(255)),
        ("phonenumber", sa.String(50)),
        ("applied_at", sa.DateTime()),
        ("status", sa.String(50)),
        ("channel_detail", sa.String(255)),
    ]
    for col, type_ in maybe_cols:
        if not _has_col(conn, "candidates", col):
            try:
                op.add_column("candidates", sa.Column(col, type_, nullable=True))
            except Exception:
                # すでに別型で存在などのケースはスキップ
                pass

def downgrade():
    conn = op.get_bind()
    # 元に戻す場合だけ（通常不要）
    for col in ["channel", "name", "channel_detail", "status", "applied_at", "phonenumber", "email", "name_yomi"]:
        try:
            if _has_col(conn, "candidates", col):
                op.drop_column("candidates", col)
        except Exception:
            pass