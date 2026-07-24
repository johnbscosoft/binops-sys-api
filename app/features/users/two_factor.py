import base64
import hashlib
import hmac
import logging
import secrets
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from urllib import parse, request

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class OtpDeliveryError(RuntimeError):
    pass


@dataclass
class DeliveryResult:
    channels: list[str]
    development_otp: str | None = None


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(challenge_id, otp: str) -> str:
    message = f"{challenge_id}:{otp}".encode("utf-8")
    return hmac.new(
        settings.jwt_secret_key.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()


def verify_otp(challenge_id, otp: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(challenge_id, otp), stored_hash)


def mask_email(email: str) -> str:
    local, domain = email.split("@", 1)
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}{'*' * max(2, len(local) - len(visible))}@{domain}"


def normalize_phone_number(phone_number: str) -> str:
    number = "".join(character for character in phone_number if character.isdigit() or character == "+")
    if number.startswith("+"):
        return number
    if number.startswith("0"):
        return f"{settings.sms_default_country_code}{number[1:]}"
    return f"{settings.sms_default_country_code}{number}"


def mask_phone(phone_number: str | None) -> str | None:
    if not phone_number:
        return None
    normalized = normalize_phone_number(phone_number)
    return f"{normalized[:4]}{'*' * max(3, len(normalized) - 7)}{normalized[-3:]}"


def deliver_otp(
    user,
    otp: str,
    *,
    allow_email: bool = True,
    allow_sms: bool = True,
) -> DeliveryResult:
    channels: list[str] = []
    errors: list[str] = []

    if allow_email and settings.smtp_host and settings.smtp_from_email:
        try:
            _send_email(user.email, otp)
            channels.append("email")
        except Exception:
            logger.exception("Email OTP delivery failed")
            errors.append("email")

    if (
        allow_sms
        and user.phone_number
        and settings.twilio_account_sid
        and settings.twilio_auth_token
        and settings.twilio_from_number
    ):
        try:
            _send_sms(user.phone_number, otp)
            channels.append("sms")
        except Exception:
            logger.exception("SMS OTP delivery failed")
            errors.append("sms")

    if not channels and settings.otp_development_mode:
        logger.warning("Development OTP for %s: %s", user.email, otp)
        return DeliveryResult(channels=["development"], development_otp=otp)

    if not channels:
        enabled_channels = " and ".join(
            channel
            for channel, enabled in (("email", allow_email), ("SMS", allow_sms))
            if enabled
        )
        failed = ", ".join(errors) if errors else enabled_channels
        raise OtpDeliveryError(
            f"OTP delivery is unavailable ({failed}). Configure SMTP or Twilio."
        )

    return DeliveryResult(channels=channels)


def _send_email(recipient: str, otp: str) -> None:
    message = EmailMessage()
    message["Subject"] = f"{settings.app_name} login verification code"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        "\n".join(
            [
                f"Your {settings.app_name} verification code is: {otp}",
                "",
                f"This code expires in {settings.otp_expire_minutes} minutes.",
                "Do not share this code with anyone.",
            ]
        )
    )

    if settings.smtp_use_ssl:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            _smtp_login_and_send(smtp, message)
        return

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        _smtp_login_and_send(smtp, message)


def _smtp_login_and_send(smtp, message: EmailMessage) -> None:
    if settings.smtp_username and settings.smtp_password:
        smtp.login(settings.smtp_username, settings.smtp_password)
    smtp.send_message(message)


def _send_sms(phone_number: str, otp: str) -> None:
    account_sid = settings.twilio_account_sid or ""
    endpoint = (
        f"https://api.twilio.com/2010-04-01/Accounts/{parse.quote(account_sid)}/Messages.json"
    )
    payload = parse.urlencode(
        {
            "To": normalize_phone_number(phone_number),
            "From": settings.twilio_from_number,
            "Body": (
                f"Your {settings.app_name} verification code is {otp}. "
                f"It expires in {settings.otp_expire_minutes} minutes."
            ),
        }
    ).encode("utf-8")
    credentials = base64.b64encode(
        f"{account_sid}:{settings.twilio_auth_token}".encode("utf-8")
    ).decode("ascii")
    sms_request = request.Request(
        endpoint,
        data=payload,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with request.urlopen(sms_request, timeout=15) as response:
        if response.status not in {200, 201}:
            raise OtpDeliveryError("SMS provider rejected the message")
