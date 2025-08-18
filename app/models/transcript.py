from ..extensions import db
from .base import OrgScopedMixin, TimestampMixin

class Transcript(db.Model, OrgScopedMixin, TimestampMixin):
    __tablename__ = "transcripts"
    id = db.Column(db.Integer, primary_key=True)
    recording_id = db.Column(db.Integer, db.ForeignKey("recordings.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    lang = db.Column(db.String(10), default="ja")
    # raw utterances/diarization data (Deepgram 'utterances' or similar)
    utterances = db.Column(db.JSON, nullable=True)
    # computed speaking metrics (output of speaking_metrics_from_utterances)
    metrics = db.Column(db.JSON, nullable=True)