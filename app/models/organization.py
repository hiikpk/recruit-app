from ..extensions import db
from .base import TimestampMixin

class Organization(db.Model, TimestampMixin):
    __tablename__ = "organizations"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)