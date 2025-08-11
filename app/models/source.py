from ..extensions import db
from .base import OrgScopedMixin, TimestampMixin

class Source(db.Model, OrgScopedMixin, TimestampMixin):
    __tablename__ = "sources"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)