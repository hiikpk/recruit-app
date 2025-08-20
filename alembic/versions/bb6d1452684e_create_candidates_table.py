from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "bb6d1452684e"               # 自動生成されたIDのままでOK
down_revision = "9376c3b92e7b"      # ★ここが肝：baseの直後に入れる
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "candidates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        # ここに後続が期待する最小限のカラム（email, name 等）を入れる
        # 迷ったら models の Candidate 定義を見て「NOT NULLのもの」中心に
    )

def downgrade():
    op.drop_table("candidates")