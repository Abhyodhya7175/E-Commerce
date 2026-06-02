"""Email OTP generation, storage, and delivery."""

import secrets
import smtplib
from datetime import datetime, timedelta

from flask import current_app
from flask_mail import Message
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db, mail
from ..models import EmailOTP


class MailNotConfiguredError(RuntimeError):
    """SMTP credentials are missing; OTP cannot be emailed."""


class MailDeliveryError(RuntimeError):
    """SMTP send failed."""


def mail_is_configured() -> bool:
    if current_app.config.get("MAIL_SUPPRESS_SEND", True):
        return False
    return bool(
        current_app.config.get("MAIL_USERNAME")
        and current_app.config.get("MAIL_PASSWORD")
    )


def mail_config_hint() -> str:
    return (
        "Add MAIL_USERNAME and MAIL_PASSWORD to flask_app/.env (or project .env), "
        "then restart the server. For Gmail, create an App Password at "
        "https://myaccount.google.com/apppasswords — do not use your normal login password."
    )


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def generate_otp_code(length: int | None = None) -> str:
    length = length or int(current_app.config.get("OTP_LENGTH", 6))
    return "".join(secrets.choice("0123456789") for _ in range(length))


def create_and_send_otp(email: str, purpose: str = "login") -> None:
    email = _normalize_email(email)
    if not email:
        raise ValueError("Email is required")

    EmailOTP.query.filter_by(email=email, is_used=False).update({"is_used": True})

    code = generate_otp_code()
    expires_at = datetime.utcnow() + timedelta(
        minutes=int(current_app.config.get("OTP_EXPIRE_MINUTES", 10))
    )
    record = EmailOTP(
        email=email,
        otp=generate_password_hash(code),
        expires_at=expires_at,
    )
    db.session.add(record)
    db.session.commit()

    _send_otp_email(email, code, purpose)


def verify_otp(email: str, code: str) -> bool:
    email = _normalize_email(email)
    code = (code or "").strip()
    if not email or not code:
        return False

    record = (
        EmailOTP.query.filter_by(email=email, is_used=False)
        .order_by(EmailOTP.created_at.desc())
        .first()
    )
    if not record or record.expires_at < datetime.utcnow():
        return False
    if not check_password_hash(record.otp, code):
        return False

    record.is_used = True
    db.session.commit()
    return True


def _format_smtp_error(exc: Exception) -> str:
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return (
            "SMTP login failed. For Gmail, use an App Password (not your normal password) "
            "and set MAIL_USERNAME to your full Gmail address."
        )
    if isinstance(exc, smtplib.SMTPConnectError):
        return (
            f"Could not connect to mail server {current_app.config.get('MAIL_SERVER')}:"
            f"{current_app.config.get('MAIL_PORT')}. Check MAIL_SERVER, MAIL_PORT, "
            "MAIL_USE_TLS, and your network/firewall."
        )
    if isinstance(exc, smtplib.SMTPException):
        return f"Mail server error: {exc}"
    return str(exc) or "Unknown mail error"


def _send_otp_email(email: str, code: str, purpose: str) -> None:
    app_name = current_app.config.get("APP_NAME", "UrbanCart")
    if purpose == "register":
        subject = f"{app_name} — verify your email"
        intro = "Use this code to complete your registration:"
    else:
        subject = f"{app_name} — your sign-in code"
        intro = "Use this code to sign in to your account:"

    minutes = current_app.config.get("OTP_EXPIRE_MINUTES", 10)
    body = (
        f"Hello,\n\n{intro}\n\n"
        f"  {code}\n\n"
        f"This code expires in {minutes} minutes. "
        "If you did not request this, you can ignore this email.\n\n"
        f"— {app_name}"
    )
    html = (
        f"<p>Hello,</p><p>{intro}</p>"
        f'<p style="font-size:24px;font-weight:bold;letter-spacing:4px;">{code}</p>'
        f"<p>This code expires in {minutes} minutes.</p>"
        f"<p>— {app_name}</p>"
    )

    if current_app.config.get("MAIL_SUPPRESS_SEND"):
        current_app.logger.warning(
            "MAIL_SUPPRESS_SEND is on — OTP for %s (%s): %s (not emailed)",
            email,
            purpose,
            code,
        )
        raise MailNotConfiguredError(mail_config_hint())

    sender = current_app.config.get("MAIL_DEFAULT_SENDER")
    if not sender:
        raise MailNotConfiguredError("MAIL_DEFAULT_SENDER is not set. " + mail_config_hint())

    msg = Message(
        subject=subject,
        recipients=[email],
        body=body,
        html=html,
        sender=sender,
    )
    try:
        mail.send(msg)
        current_app.logger.info("OTP email sent to %s (%s)", email, purpose)
    except Exception as exc:
        current_app.logger.exception("Failed to send OTP email to %s", email)
        raise MailDeliveryError(_format_smtp_error(exc)) from exc
