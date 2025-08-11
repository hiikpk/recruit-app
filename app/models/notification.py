from ..extensions import db
from .base import OrgScopedMixin, TimestampMixin

class Notification(db.Model, OrgScopedMixin, TimestampMixin):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False)
    type = db.Column(db.String(50))
    sent_to = db.Column(db.String(255))
    subject = db.Column(db.String(255))
    body = db.Column(db.Text)
    provider_message_id = db.Column(db.String(255))
    sent_at = db.Column(db.DateTime)