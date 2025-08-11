from ..extensions import db
from .base import OrgScopedMixin, TimestampMixin

class Recording(db.Model, OrgScopedMixin, TimestampMixin):
    __tablename__ = "recordings"
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey("interviews.id"), nullable=False)
    storage_url = db.Column(db.String(512), nullable=False)
    duration_sec = db.Column(db.Integer)
    uploaded_by = db.Column(db.Integer)  # user id