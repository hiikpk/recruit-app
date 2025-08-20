"""idempotent: add scheduled_at to interviews if missing

Revision ID: 20250820_add_scheduled_at_to_interviews
Revises: 20250820_add_org_id_to_users
Create Date: 2025-08-20 20:10:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250820_add_scheduled_at_to_interviews"
down_revision = "20250820_add_org_id_to_users"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "interviews" in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('interviews')}
        if 'scheduled_at' not in cols:
            # SQLite needs batch_alter_table, Postgres will ignore if not needed
            try:
                with op.batch_alter_table('interviews') as batch:
                    batch.add_column(sa.Column('scheduled_at', sa.DateTime(), nullable=True))
            except Exception:
                # fallback simple add (for Postgres/others)
                op.add_column('interviews', sa.Column('scheduled_at', sa.DateTime(), nullable=True))


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "interviews" in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('interviews')}
        if 'scheduled_at' in cols:
            try:
                with op.batch_alter_table('interviews') as batch:
                    batch.drop_column('scheduled_at')
            except Exception:
                op.drop_column('interviews', 'scheduled_at')
