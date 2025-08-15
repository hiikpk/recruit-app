from ..extensions import db
from .base import OrgScopedMixin, TimestampMixin

class Candidate(db.Model, OrgScopedMixin, TimestampMixin):
    __tablename__ = "candidates"

    id = db.Column(db.Integer, primary_key=True)
    # OrgScopedMixin: org_id
    name = db.Column(db.String(120), nullable=False)
    name_yomi = db.Column(db.String(160))
    email = db.Column(db.String(254), unique=True, index=True)
    phonenumber = db.Column(db.String(40))
    birthdate = db.Column(db.Date)
    memo = db.Column(db.Text)

    # スキル・経歴
    school = db.Column(db.String(200))
    grad_year = db.Column(db.Integer)
    current_job = db.Column(db.Text)
    resume_file_id = db.Column(db.Integer, db.ForeignKey("files.id"))  # 任意
    qualifications = db.Column(db.JSON)  # ["基本情報","TOEIC800"]
    languages = db.Column(db.JSON)       # [{"lang":"EN","level":"B2"}]
    skills = db.Column(db.JSON)          # ["Python","Flask","SQL"]

    # 選考情報
    applied_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    status = db.Column(db.String(30), index=True)  # applied/screening/offer/hired/rejected/withdrawn
    offer_date = db.Column(db.Date)
    acceptance_date = db.Column(db.Date)
    join_date = db.Column(db.Date)
    decline_date = db.Column(db.Date)
    channel = db.Column(db.String(50))
    channel_detail = db.Column(db.String(200))

    # 外部キー/メタ
    evaluate_key = db.Column(db.String(64))  # UUID/任意

    def __repr__(self) -> str:
        return f"<Candidate id={self.id} name={self.name!r}>"