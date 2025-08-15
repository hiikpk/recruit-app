from ..extensions import db
from .base import OrgScopedMixin

class CandidateOverallEvaluation(db.Model, OrgScopedMixin):
    __tablename__ = "candidate_overall_evaluations"

    id = db.Column(db.Integer, primary_key=True)
    # OrgScopedMixin: org_id
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id"), nullable=False)

    # 履歴
    version = db.Column(db.Integer, nullable=False, default=1)

    # 集計元
    aggregated_from = db.Column(db.JSON)  # interview_evaluations.id の配列

    # スコア
    overall_score = db.Column(db.Numeric(5, 2))
    speaking = db.Column(db.Numeric(5, 2))
    logical = db.Column(db.Numeric(5, 2))
    volume = db.Column(db.Numeric(5, 2))
    honesty = db.Column(db.Numeric(5, 2))
    proactive = db.Column(db.Numeric(5, 2))

    # 要約/監査
    gpt_summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<CandidateOverallEvaluation id={self.id} candidate_id={self.candidate_id}>"