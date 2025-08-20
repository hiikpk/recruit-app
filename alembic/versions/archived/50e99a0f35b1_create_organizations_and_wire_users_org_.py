# alembic/versions/XXXXXXXXXXXX_create_organizations_and_wire_users.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# ↓適切に置き換わります
revision = '20250820_create_orgs'
down_revision = '20250820_add_org_id_to_users'
branch_labels = None
depends_on = None

def _has_table(conn, name: str) -> bool:
    insp = Inspector.from_engine(conn)
    return insp.has_table(name)

def _has_column(conn, table: str, column: str) -> bool:
    insp = Inspector.from_engine(conn)
    return any(c["name"] == column for c in insp.get_columns(table))

def upgrade():
    conn = op.get_bind()

    # 1) organizations テーブルが無ければ作成
    if not _has_table(conn, "organizations"):
        op.create_table(
            "organizations",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.String(255), nullable=False, unique=True),
            sa.Column("created_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
        )

        # 最低 1 件デフォルト行（signup 初期化用）
        op.execute(
            "INSERT INTO organizations (name) VALUES ('default') "
            "ON CONFLICT (name) DO NOTHING"
        )

    # 2) users.org_id を追加（無ければ）
    if _has_table(conn, "users") and not _has_column(conn, "users", "org_id"):
        op.add_column("users", sa.Column("org_id", sa.Integer, nullable=True))
        # 既存ユーザーの org_id を default に寄せる（無ければ作って取得）
        op.execute("""
        WITH upsert AS (
            INSERT INTO organizations (name)
            VALUES ('default')
            ON CONFLICT (name) DO NOTHING
            RETURNING id
        )
        UPDATE users
        SET org_id = COALESCE(
            (SELECT id FROM upsert),
            (SELECT id FROM organizations WHERE name='default' LIMIT 1)
        )
        WHERE org_id IS NULL
        """)

        # 外部キー（存在すれば二重作成されないよう名前で IF NOT EXISTS 的に try）
        try:
            op.create_foreign_key(
                "fk_users_org_id_organizations",
                "users",
                "organizations",
                ["org_id"],
                ["id"],
                ondelete="SET NULL",
            )
        except Exception:
            # 既に存在すれば無視
            pass

def downgrade():
    conn = op.get_bind()
    # 外部キーを消す（あれば）
    try:
        op.drop_constraint("fk_users_org_id_organizations", "users", type_="foreignkey")
    except Exception:
        pass
    # users.org_id を落とす（あれば）
    insp = Inspector.from_engine(conn)
    if insp.has_table("users") and any(c["name"] == "org_id" for c in insp.get_columns("users")):
        op.drop_column("users", "org_id")
    # organizations はアプリの前提になるので基本残すが、どうしても戻すならコメントアウト解除
    # if insp.has_table("organizations"):
    #     op.drop_table("organizations")