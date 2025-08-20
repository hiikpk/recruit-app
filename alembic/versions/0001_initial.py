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

    # Drop all existing tables (if any) then create all tables from models.
    db.metadata.drop_all(bind=bind)
    db.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    from app.extensions import db
    # Downgrade: drop all tables created by this migration.
    db.metadata.drop_all(bind=bind)
