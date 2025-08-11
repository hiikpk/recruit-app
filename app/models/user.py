from ..extensions import db
from flask_login import UserMixin
from .base import TimestampMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin, TimestampMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default="admin")

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)