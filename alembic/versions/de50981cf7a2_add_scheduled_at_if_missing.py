"""add scheduled_at to interviews if missing"""

from alembic import op
import sqlalchemy as sa

# 適当な revision / down_revision を設定（あなたの環境に合わせて）
revision = "20250820_add_interviews_scheduled_at"
down_revision = "m20250820a001"  # ← 必ず正しく書き換える

def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns("interviews")]
    if "scheduled_at" not in cols:
        op.add_column(
            "interviews",
            sa.Column("scheduled_at", sa.DateTime(timezone=False), nullable=True),
        )
        # 既存データのフォールバック（なければ created_at を入れておく）
        op.execute(
            sa.text(
                "UPDATE interviews SET scheduled_at = created_at WHERE scheduled_at IS NULL"
            )
        )
        # よく使うならインデックスを貼る
        op.create_index(
            "ix_interviews_scheduled_at", "interviews", ["scheduled_at"], unique=False
        )

def downgrade():
    # 取り外し
    bind = op.get_bind()
    insp = sa.inspect(bind)
    idxes = [i["name"] for i in insp.get_indexes("interviews")]
    if "ix_interviews_scheduled_at" in idxes:
        op.drop_index("ix_interviews_scheduled_at", table_name="interviews")
    cols = [c["name"] for c in insp.get_columns("interviews")]
    if "scheduled_at" in cols:
        op.drop_column("interviews", "scheduled_at")