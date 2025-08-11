from ..extensions import db
from .base import OrgScopedMixin, TimestampMixin

class Application(db.Model, OrgScopedMixin, TimestampMixin):
    __tablename__ = "applications"
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id"), nullable=False)
    status = db.Column(db.String(50), default="screening")
    stage = db.Column(db.String(50), default="document")
    score_avg = db.Column(db.Float)
    last_evaluated_at = db.Column(db.DateTime)

    def latest_transcript_text(self):
        q = db.text(
            """
            SELECT t.text FROM transcripts t
            JOIN recordings r ON r.id = t.recording_id
            JOIN interviews i ON i.id = r.interview_id
            WHERE i.application_id = :app_id
            ORDER BY t.created_at DESC
            LIMIT 1
            """
        )
        res = db.session.execute(q, {"app_id": self.id}).fetchone()
        return res[0] if res else ""