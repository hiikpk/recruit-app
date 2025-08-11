from ..extensions import db

class OrgScopedMixin:
    org_id = db.Column(db.Integer, nullable=False, index=True)

class TimestampMixin:
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())