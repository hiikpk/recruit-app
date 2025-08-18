from ..extensions import db
from .base import OrgScopedMixin, TimestampMixin


class Setting(db.Model, OrgScopedMixin, TimestampMixin):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(128), nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('org_id', 'key', name='uq_settings_org_key'),
    )

    def __repr__(self):
        return f"<Setting org_id={self.org_id} key={self.key} value={self.value}>"
