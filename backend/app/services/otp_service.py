"""Short-lived, hashed email OTP generation and delivery boundary."""

from email.message import EmailMessage
import secrets
import smtplib
from app.core.config import settings
from app.core.security import pwd_context


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(code: str) -> str:
    return pwd_context.hash(code)


def verify_otp(code: str, code_hash: str) -> bool:
    return pwd_context.verify(code, code_hash)


def send_otp_email(email: str, code: str) -> None:
    """Send the verification code through configured SMTP credentials."""
    if not settings.OTP_SMTP_HOST or not settings.OTP_FROM_ADDRESS:
        raise RuntimeError("OTP email delivery is not configured")
    message = EmailMessage()
    message["Subject"] = "Your CampaignIQ verification code"
    message["From"] = settings.OTP_FROM_ADDRESS
    message["To"] = email
    message.set_content(f"Your CampaignIQ verification code is {code}. It expires soon.")
    smtp_factory = smtplib.SMTP_SSL if settings.OTP_SMTP_PORT == 465 else smtplib.SMTP
    with smtp_factory(settings.OTP_SMTP_HOST, settings.OTP_SMTP_PORT, timeout=15) as smtp:
        if settings.OTP_SMTP_PORT != 465:
            smtp.starttls()
        if settings.OTP_SMTP_USERNAME:
            smtp.login(settings.OTP_SMTP_USERNAME, settings.OTP_SMTP_PASSWORD)
        smtp.send_message(message)
