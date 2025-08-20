from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine import reflection

# revision identifiers, used by Alembic.
revision = "83ff2ec11d22"        # ←自動生成された値のままでOK
down_revision = "00a330981fad"   # ←自動生成された値のままでOK
branch_labels = None
depends_on = None


def _has_table(conn, name: str) -> bool:
    insp = reflection.Inspector.from_engine(conn)
    return insp.has_table(name)


def _columns(conn, table: str):
    insp = reflection.Inspector.from_engine(conn)
    return {c["name"] for c in insp.get_columns(table)}


def _ensure_column(conn, table: str, name: str, column: sa.Column):
    if name not in _columns(conn, table):
        op.add_column(table, column)


def upgrade():
    conn = op.get_bind()

    # candidates テーブルがなければ最低限で用意
    if not _has_table(conn, "candidates"):
        op.create_table(
            "candidates",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("created_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
        )

    # まとめて不足カラムを補完（型は保守的に、NULL許可で）
    _ensure_column(conn, "candidates", "name",               sa.Column("name", sa.String(255), nullable=True))
    _ensure_column(conn, "candidates", "name_yomi",          sa.Column("name_yomi", sa.String(255), nullable=True))
    _ensure_column(conn, "candidates", "email",              sa.Column("email", sa.String(255), nullable=True))
    _ensure_column(conn, "candidates", "phonenumber",        sa.Column("phonenumber", sa.String(64), nullable=True))
    _ensure_column(conn, "candidates", "birthdate",          sa.Column("birthdate", sa.Date(), nullable=True))
    _ensure_column(conn, "candidates", "memo",               sa.Column("memo", sa.Text(), nullable=True))
    _ensure_column(conn, "candidates", "applying_position",  sa.Column("applying_position", sa.String(255), nullable=True))
    _ensure_column(conn, "candidates", "nationality",        sa.Column("nationality", sa.String(255), nullable=True))
    _ensure_column(conn, "candidates", "school",             sa.Column("school", sa.String(255), nullable=True))
    _ensure_column(conn, "candidates", "grad_year",          sa.Column("grad_year", sa.Integer(), nullable=True))
    _ensure_column(conn, "candidates", "current_job",        sa.Column("current_job", sa.String(255), nullable=True))
    _ensure_column(conn, "candidates", "resume_file_id",     sa.Column("resume_file_id", sa.Integer(), nullable=True))
    _ensure_column(conn, "candidates", "qualifications",     sa.Column("qualifications", sa.Text(), nullable=True))
    _ensure_column(conn, "candidates", "languages",          sa.Column("languages", sa.Text(), nullable=True))
    _ensure_column(conn, "candidates", "skills",             sa.Column("skills", sa.Text(), nullable=True))
    _ensure_column(conn, "candidates", "applied_at",         sa.Column("applied_at", sa.DateTime(), nullable=True))
    _ensure_column(conn, "candidates", "status",             sa.Column("status", sa.String(64), nullable=True))
    _ensure_column(conn, "candidates", "offer_date",         sa.Column("offer_date", sa.Date(), nullable=True))
    _ensure_column(conn, "candidates", "acceptance_date",    sa.Column("acceptance_date", sa.Date(), nullable=True))
    _ensure_column(conn, "candidates", "join_date",          sa.Column("join_date", sa.Date(), nullable=True))
    _ensure_column(conn, "candidates", "decline_date",       sa.Column("decline_date", sa.Date(), nullable=True))
    _ensure_column(conn, "candidates", "channel",            sa.Column("channel", sa.String(255), nullable=True))
    _ensure_column(conn, "candidates", "channel_detail",     sa.Column("channel_detail", sa.String(255), nullable=True))
    _ensure_column(conn, "candidates", "evaluate_key",       sa.Column("evaluate_key", sa.String(64), nullable=True))

    # org_id は既に追加済みのはずだが念のため
    if "org_id" not in _columns(conn, "candidates"):
        op.add_column("candidates", sa.Column("org_id", sa.Integer(), nullable=True))
    # インデックス（存在しなければ作成）
    insp = reflection.Inspector.from_engine(conn)
    existing_idx = {i["name"] for i in insp.get_indexes("candidates")}
    if "ix_candidates_org_id" not in existing_idx and "org_id" in _columns(conn, "candidates"):
        op.create_index("ix_candidates_org_id", "candidates", ["org_id"])


def downgrade():
    # 破壊的変更は最小限（本番データ保護のため基本は何もしない）
    pass