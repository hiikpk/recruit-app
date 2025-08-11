from ..extensions import db
from .base import OrgScopedMixin, TimestampMixin

class Interview(db.Model, OrgScopedMixin, TimestampMixin):
    __tablename__ = "interviews"
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False)
    scheduled_start = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(255))
    meeting_url = db.Column(db.String(255))
    ics_token = db.Column(db.String(255))
    status = db.Column(db.String(50), default="scheduled")
    step = db.Column(db.String(20))       # document / first / second / final
    rank = db.Column(db.String(2))        # S/A/B/C
    decision = db.Column(db.String(20))   # pass/fail/other
    comment = db.Column(db.Text)
    interviewer = db.Column(db.String(120))