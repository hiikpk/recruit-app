"""align interviews table to current model (add columns if missing)"""

from alembic import op
import sqlalchemy as sa

# Alembic identifiers (keep these short to fit alembic_version.varchar(32))
revision = "de50981cf7a2"  # this file's slug
# TODO: set to your actual previous revision id
down_revision = "20250820_add_scheduled_at_to_interviews"
branch_labels = None
depends_on = None


# Columns expected by the current Interview model
_EXPECTED_COLS = {
    # name: (type_, kwargs)
    "scheduled_at": (sa.DateTime(timezone=False), {"nullable": True}),
    "status": (sa.String(20), {"nullable": True}),
    "result": (sa.String(20), {"nullable": True}),
    "comment": (sa.Text(), {"nullable": True}),
    "interviewer_id": (sa.Integer(), {"nullable": True}),
    "ai_score": (sa.Numeric(5, 2), {"nullable": True}),
    "transcript_text": (sa.Text(), {"nullable": True}),
    "rank": (sa.String(2), {"nullable": True}),
    "decision": (sa.String(20), {"nullable": True}),
    "interviewer": (sa.String(120), {"nullable": True}),
}


def _has_table(inspector, table_name: str):
    try:
        return table_name in inspector.get_table_names()
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not _has_table(insp, "interviews"):
        # If the table doesn't exist yet, do nothing here; another migration should create it.
        return

    existing_cols = {c["name"] for c in insp.get_columns("interviews")}

    # Add any missing columns, matching the model's definition (all nullable)
    for col_name, (col_type, kwargs) in _EXPECTED_COLS.items():
        if col_name not in existing_cols:
            op.add_column("interviews", sa.Column(col_name, col_type, **kwargs))

    # Backfill scheduled_at from created_at when newly added and still NULL
    if "scheduled_at" not in existing_cols:
        op.execute(sa.text(
            "UPDATE interviews SET scheduled_at = created_at WHERE scheduled_at IS NULL"
        ))
        # Index for common ordering/filtering
        try:
            op.create_index("ix_interviews_scheduled_at", "interviews", ["scheduled_at"], unique=False)
        except Exception:
            # Best-effort; ignore if it already exists
            pass


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not _has_table(insp, "interviews"):
        return

    # Drop index if present
    try:
        idx_names = {i["name"] for i in insp.get_indexes("interviews")}
        if "ix_interviews_scheduled_at" in idx_names:
            op.drop_index("ix_interviews_scheduled_at", table_name="interviews")
    except Exception:
        pass

    # Remove columns we added (safe if they exist)
    existing_cols = {c["name"] for c in insp.get_columns("interviews")}
    for col_name in _EXPECTED_COLS.keys():
        if col_name in existing_cols:
            op.drop_column("interviews", col_name)