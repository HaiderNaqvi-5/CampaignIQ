"""Single campaign delivery interface; SMTP is the v1 provider."""

from email.message import EmailMessage
import smtplib
from typing import Protocol
from app.core.config import settings


class EmailProvider(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


class SMTPEmailProvider:
    def send(self, to: str, subject: str, body: str) -> None:
        if not settings.CAMPAIGN_SMTP_HOST or not settings.CAMPAIGN_EMAIL_FROM_ADDRESS:
            raise RuntimeError("Campaign SMTP delivery is not configured")
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.CAMPAIGN_EMAIL_FROM_ADDRESS
        message["To"] = to
        message.set_content(body)
        factory = smtplib.SMTP_SSL if settings.CAMPAIGN_SMTP_PORT == 465 else smtplib.SMTP
        with factory(settings.CAMPAIGN_SMTP_HOST, settings.CAMPAIGN_SMTP_PORT, timeout=20) as smtp:
            if settings.CAMPAIGN_SMTP_PORT != 465:
                smtp.starttls()
            if settings.CAMPAIGN_SMTP_USERNAME:
                smtp.login(settings.CAMPAIGN_SMTP_USERNAME, settings.CAMPAIGN_SMTP_PASSWORD)
            smtp.send_message(message)


def get_email_provider() -> SMTPEmailProvider:
    return SMTPEmailProvider()
