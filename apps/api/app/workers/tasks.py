import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import get_settings
from app.workers.celery_app import celery_app


@celery_app.task(name="ping")
def ping() -> str:
    return "pong"


@celery_app.task(
    name="send_email",
    autoretry_for=(OSError, smtplib.SMTPException),
    retry_backoff=True,
    max_retries=3,
)
def send_email(to: str, subject: str, body: str) -> None:
    """Send a plain-text email over SMTP (Mailpit in development)."""
    settings = get_settings()
    message = EmailMessage()
    message["From"] = formataddr((settings.smtp_from_name, settings.smtp_from_email))
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_user and settings.smtp_password:
            smtp.login(settings.smtp_user, settings.smtp_password.get_secret_value())
        smtp.send_message(message)
