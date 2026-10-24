"""Outgoing email over SMTP (any provider: Gmail app password, SendGrid, Amazon SES, ...). Configured in .env."""
import smtplib
from email.message import EmailMessage

from app.core.config import settings


class EmailNotConfigured(RuntimeError):
    pass


def is_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_FROM)


def send_email(to: str, subject: str, body: str, attachments: list | None = None):
    """attachments: [(filename, bytes, 'application/pdf'), ...]"""
    if not is_configured():
        raise EmailNotConfigured('Email sending is not set up (SMTP_HOST / SMTP_FROM in .env).')
    msg = EmailMessage()
    msg['From'] = settings.SMTP_FROM
    msg['To'] = to
    msg['Subject'] = subject
    msg.set_content(body)
    for filename, content, mime in attachments or []:
        maintype, subtype = mime.split('/', 1)
        msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as smtp:
        if settings.SMTP_STARTTLS:
            smtp.starttls()
        if settings.SMTP_USERNAME:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(msg)
