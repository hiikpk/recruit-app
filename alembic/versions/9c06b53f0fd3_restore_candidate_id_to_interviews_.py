"""restore candidate_id to interviews (idempotent)"""

from alembic import op
import sqlalchemy as sa

# 自動生成されたIDをそのまま使う
revision = "9c06b53f0fd3"
down_revision = "m20250815a001"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("interviews")}

    # SQLite なので batch_alter_table で安全に
    with op.batch_alter_table("interviews") as batch:
        if "candidate_id" not in cols:
            batch.add_column(sa.Column("candidate_id", sa.Integer(), nullable=True))

    # インデックスは存在しなければ作成
    idx_names = {i["name"] for i in insp.get_indexes("interviews")}
    if "ix_interviews_candidate_id" not in idx_names:
        op.create_index("ix_interviews_candidate_id", "interviews", ["candidate_id"])

    # 参考: 外部キーは SQLite の後付け制約が弱いので省略か、必要なら再作成パス
    # op.create_foreign_key("fk_interviews_candidate_id", "interviews", "candidates",
    #                       ["candidate_id"], ["id"], ondelete="SET NULL")

def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    idx_names = {i["name"] for i in insp.get_indexes("interviews")}
    if "ix_interviews_candidate_id" in idx_names:
        op.drop_index("ix_interviews_candidate_id", table_name="interviews")

    cols = {c["name"] for c in insp.get_columns("interviews")}
    with op.batch_alter_table("interviews") as batch:
        if "candidate_id" in cols:
            batch.drop_column("candidate_id")