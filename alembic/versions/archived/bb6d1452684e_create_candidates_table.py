from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "bb6d1452684e"               # 自動生成されたIDのままでOK
down_revision = "9376c3b92e7b"      # ★ここが肝：baseの直後に入れる
branch_labels = None
depends_on = None

def upgrade():
    # users（必要最小限）
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
    )

    # candidates（すでに作っていればその内容に合わせる）
    op.create_table(
        "candidates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
        # 後続が参照/変更する可能性の高い列があれば最低限いれておく（email/name等）
    )

    # interviews（後続でupdate/dropされるなら、先に“存在”させる）
    op.create_table(
        "interviews",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("candidate_id", sa.Integer, sa.ForeignKey("candidates.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
        # 後続の migration が alter/drop する対象があれば最低限の“叩き台”だけ用意
    )

    # transcripts
    op.create_table(
        "transcripts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
    )

def downgrade():
    op.drop_table("interviews")
    op.drop_table("candidates")
    op.drop_table("users")