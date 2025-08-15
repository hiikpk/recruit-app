from ..extensions import db
from .base import OrgScopedMixin, TimestampMixin

class Files(db.Model, OrgScopedMixin, TimestampMixin):
    __tablename__ = "files"

    id = db.Column(db.Integer, primary_key=True)
    # OrgScopedMixin: org_id
    org_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=False)

    kind = db.Column(db.String(20))  # resume/audio/ics/other
    storage_url = db.Column(db.String(255), nullable=True)
    file_metadata = db.Column(db.JSON)  # {"filename": "example.pdf", "size": 123456, "content_type": "application/pdf"}
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)