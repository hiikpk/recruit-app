from ..extensions import db
from .base import OrgScopedMixin, TimestampMixin

class Interview(db.Model, OrgScopedMixin, TimestampMixin):
    __tablename__ = "interviews"

    id = db.Column(db.Integer, primary_key=True)
    # OrgScopedMixin: org_id
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id"), nullable=False)

    # 選考
    step = db.Column(db.String(20))  # document/first/second/final
    scheduled_at = db.Column(db.DateTime)  # 実施日時
    # ics_token = db.Column(db.String(64))   # 招待/再発行の識別子
    status = db.Column(db.String(20))      # scheduled/done/no_show/canceled
    result = db.Column(db.String(20))      # pass/fail/pending
    comment = db.Column(db.Text)
    interviewer_id = db.Column(db.Integer)  # users.id（任意）
    ai_score = db.Column(db.Numeric(5, 2))  # 任意

    def __repr__(self) -> str:
        return f"<Interview id={self.id} candidate_id={self.candidate_id}>"