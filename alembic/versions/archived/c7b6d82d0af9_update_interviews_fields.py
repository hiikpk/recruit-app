# """update interviews fields

# Revision ID: c7b6d82d0af9
# Revises: a7c308c97029
# Create Date: 2025-08-10
# """

# from alembic import op
# import sqlalchemy as sa

# # revision identifiers, used by Alembic.
# revision = 'c7b6d82d0af9'
# down_revision = 'a7c308c97029'
# branch_labels = None
# depends_on = None


# def upgrade():
# 	with op.batch_alter_table('interviews') as batch_op:
# 		# drop old end time
# 		try:
# 			batch_op.drop_column('scheduled_end')
# 		except Exception:
# 			pass
# 		# add new columns
# 		batch_op.add_column(sa.Column('candidate_id', sa.Integer(), nullable=True))
# 		batch_op.add_column(sa.Column('rank', sa.String(length=2), nullable=True))
# 		batch_op.add_column(sa.Column('decision', sa.String(length=20), nullable=True))
# 		batch_op.add_column(sa.Column('comment', sa.Text(), nullable=True))
# 		batch_op.add_column(sa.Column('interviewer', sa.String(length=120), nullable=True))


# def downgrade():
# 	with op.batch_alter_table('interviews') as batch_op:
# 		batch_op.drop_column('interviewer')
# 		batch_op.drop_column('comment')
# 		batch_op.drop_column('decision')
# 		batch_op.drop_column('rank')
# 		batch_op.drop_column('candidate_id')
# 		batch_op.add_column(sa.Column('scheduled_end', sa.DateTime(), nullable=True))

"""update interviews fields

Revision ID: c7b6d82d0af9
Revises: a7c308c97029
Create Date: 2025-08-10
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c7b6d82d0af9'
down_revision = 'a7c308c97029'
branch_labels = None
depends_on = None


def upgrade():
    # 実DBの列一覧を取得して、存在チェックしながら変更する（冪等化）
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("interviews")}

    # 既存列の削除（存在する時だけ）
    with op.batch_alter_table('interviews') as batch_op:
        if 'scheduled_end' in cols:
            batch_op.drop_column('scheduled_end')

        # 追加列（無い時だけ追加）
        if 'candidate_id' not in cols:
            batch_op.add_column(sa.Column('candidate_id', sa.Integer(), nullable=True))
        if 'rank' not in cols:
            batch_op.add_column(sa.Column('rank', sa.String(length=2), nullable=True))
        if 'decision' not in cols:
            batch_op.add_column(sa.Column('decision', sa.String(length=20), nullable=True))
        if 'comment' not in cols:
            batch_op.add_column(sa.Column('comment', sa.Text(), nullable=True))
        if 'interviewer' not in cols:
            batch_op.add_column(sa.Column('interviewer', sa.String(length=120), nullable=True))


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("interviews")}

    with op.batch_alter_table('interviews') as batch_op:
        if 'interviewer' in cols:
            batch_op.drop_column('interviewer')
        if 'comment' in cols:
            batch_op.drop_column('comment')
        if 'decision' in cols:
            batch_op.drop_column('decision')
        if 'rank' in cols:
            batch_op.drop_column('rank')
        if 'candidate_id' in cols:
            batch_op.drop_column('candidate_id')
        if 'scheduled_end' not in cols:
            batch_op.add_column(sa.Column('scheduled_end', sa.DateTime(), nullable=True))