"""Initial destructive baseline migration

This migration drops all tables and recreates them from the current SQLAlchemy
models/metadata. This is intentionally destructive — use only when you accept
data loss (user requested option B).

Revision ID: 0001_initial
Revises: None
Create Date: 2025-08-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Destructive: drop all tables then recreate them from SQLAlchemy metadata.
    bind = op.get_bind()
    # Import the app's db (Flask-SQLAlchemy) and use its metadata
    # to recreate the entire schema according to current models.
    from app.extensions import db

    # Drop all existing tables in a deterministic order using CASCADE to
    # avoid circular FK drop issues on Postgres. We iterate table names
    # from metadata and emit DROP TABLE IF EXISTS <name> CASCADE.
    # After that, recreate using metadata.create_all().
    meta = db.metadata
    # collect table names
    tbls = [t.name for t in meta.sorted_tables]
    # reverse to attempt to drop dependents first (best-effort)
    for t in reversed(tbls):
        bind.execute(sa.text(f'DROP TABLE IF EXISTS "{t}" CASCADE'))
    # finally recreate all tables from models
    meta.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    from app.extensions import db
    # Downgrade: drop all tables created by this migration using CASCADE.
    meta = db.metadata
    tbls = [t.name for t in meta.sorted_tables]
    for t in reversed(tbls):
        bind.execute(sa.text(f'DROP TABLE IF EXISTS "{t}" CASCADE'))
