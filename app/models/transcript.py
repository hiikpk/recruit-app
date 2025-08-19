from ..extensions import db
from .base import OrgScopedMixin, TimestampMixin

class Transcript(db.Model, OrgScopedMixin, TimestampMixin):
    __tablename__ = "transcripts"
    id = db.Column(db.Integer, primary_key=True)
    recording_id = db.Column(db.Integer, db.ForeignKey("recordings.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    lang = db.Column(db.String(10), default="ja")
    # processing status: pending -> processing -> ok -> error
    status = db.Column(db.String(20), default='pending')
    # optional short error message when status == 'error'
    error = db.Column(db.Text, nullable=True)
    # raw utterances/diarization data (Deepgram 'utterances' or similar)
    utterances = db.Column(db.JSON, nullable=True)
    # computed speaking metrics (output of speaking_metrics_from_utterances)
    metrics = db.Column(db.JSON, nullable=True)