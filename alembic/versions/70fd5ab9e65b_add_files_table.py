from alembic import op
import sqlalchemy as sa

revision = "70fd5ab9e65b"
down_revision = "251da0c7942c"   # 既にそうなっていればOK
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # テーブルが無いときだけ作成（冪等化）
    if not insp.has_table("files"):
        op.create_table(
            "files",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("filename", sa.String(255), nullable=False),
            sa.Column("path", sa.String(512), nullable=False),
            sa.Column("content_type", sa.String(128)),
            sa.Column("size", sa.Integer),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
            sa.Column("updated_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
        )
    # もしインデックス等を追加するなら、存在確認してから op.create_index(...)

def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    # あるときだけ落とす（冪等化）
    if insp.has_table("files"):
        op.drop_table("files")