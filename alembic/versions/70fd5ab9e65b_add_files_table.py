from alembic import op
import sqlalchemy as sa

revision = "70fd5ab9e65b"
down_revision = "251da0c7942c"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "files",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(128)),
        sa.Column("size", sa.Integer),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

def downgrade():
    op.drop_table("files")
