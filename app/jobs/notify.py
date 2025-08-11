from ..extensions import db
from ..services.mail import send_decision
from ..models.notification import Notification
from datetime import datetime


def notify_decision(org_id: int, application_id: int, to_email: str, subject: str, body_html: str):
    status, headers = send_decision(to_email, subject, body_html)
    n = Notification(org_id=org_id, application_id=application_id,
                     type="sendgrid", sent_to=to_email, subject=subject,
                     body=body_html, provider_message_id=str(headers or ""),
                     sent_at=datetime.utcnow())
    db.session.add(n); db.session.commit()
    return n.id