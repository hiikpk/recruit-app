from ..extensions import db
from .base import OrgScopedMixin, TimestampMixin

class Transcript(db.Model, OrgScopedMixin, TimestampMixin):
    __tablename__ = "transcripts"
    id = db.Column(db.Integer, primary_key=True)
    recording_id = db.Column(db.Integer, db.ForeignKey("recordings.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    lang = db.Column(db.String(10), default="ja")