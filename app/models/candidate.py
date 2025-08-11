from ..extensions import db
from .base import OrgScopedMixin, TimestampMixin

class Candidate(db.Model, OrgScopedMixin, TimestampMixin):
    __tablename__ = "candidates"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    school = db.Column(db.String(120))
    grad_year = db.Column(db.Integer)
    resume_url = db.Column(db.String(512))
    source_id = db.Column(db.Integer, db.ForeignKey("sources.id"))
    notes = db.Column(db.Text)
    birthdate = db.Column(db.Date)           # 生年月日
    applied_at = db.Column(db.DateTime)      # 応募日
    qualifications = db.Column(db.Text)      # 資格（改行 or カンマ区切り）
    skills = db.Column(db.Text)              # スキルセット（同）
    languages = db.Column(db.Text)           # 語学スキル（同）