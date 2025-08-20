# alembic/versions/20250820_add_org_id_to_users.py
from alembic import op
import sqlalchemy as sa

# ここは自分の最新 head に合わせること（例）
revision = "20250820_add_org_id_to_users"
down_revision = "m20250819a001"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # users テーブルがあるか
    if "users" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("users")}
        if "org_id" not in cols:
            op.add_column("users", sa.Column("org_id", sa.Integer(), nullable=True))

            # 組織テーブルがあるなら外部キーも（任意）
            if "organizations" in insp.get_table_names():
                # 既存に同名 FK があれば落ちるので try/except は不要、まず存在しない前提で張る
                op.create_foreign_key(
                    "fk_users_org", "users", "organizations",
                    ["org_id"], ["id"], ondelete="SET NULL"
                )

def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "users" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("users")}
        # 先に FK を落とす（あれば）
        try:
            op.drop_constraint("fk_users_org", "users", type_="foreignkey")
        except Exception:
            pass
        if "org_id" in cols:
            op.drop_column("users", "org_id")