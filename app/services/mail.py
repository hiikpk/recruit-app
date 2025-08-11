from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from flask import current_app

def send_decision(to_email, subject, html):
    sg = SendGridAPIClient(api_key=current_app.config['SENDGRID_API_KEY'])
    message = Mail(from_email=(current_app.config['MAIL_FROM'], current_app.config['MAIL_FROM_NAME']),
                   to_emails=to_email,
                   subject=subject,
                   html_content=html)
    resp = sg.send(message)
    return resp.status_code, getattr(resp, 'headers', None)