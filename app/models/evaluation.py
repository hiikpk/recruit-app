from ..extensions import db
from .base import OrgScopedMixin, TimestampMixin

class Evaluation(db.Model, OrgScopedMixin, TimestampMixin):
    __tablename__ = "evaluations"
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False)
    interviewer_id = db.Column(db.Integer)  # user id
    rubric_json = db.Column(db.JSON)
    score_total = db.Column(db.Float)
    decision = db.Column(db.String(20))  # pass/fail/hold
    gpt_summary = db.Column(db.Text)