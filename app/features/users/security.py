import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from app.core.config import get_settings

settings = get_settings()


def now_utc() -> datetime:
    return datetime.now(UTC)


def hash_password(password: str) -> str:
    # PBKDF2 is available in Python's standard library and stores the salt
    # beside the derived hash so verification can reproduce the same value.
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        260_000,
    ).hex()
    return f"pbkdf2_sha256$260000${salt}${password_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected_hash = stored_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    ).hex()
    return hmac.compare_digest(password_hash, expected_hash)


def create_plain_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def access_token_expires_at() -> datetime:
    return now_utc() + timedelta(minutes=settings.access_token_expire_minutes)


def refresh_token_expires_at() -> datetime:
    return now_utc() + timedelta(days=settings.refresh_token_expire_days)


def verification_token_expires_at() -> datetime:
    return now_utc() + timedelta(hours=settings.verification_token_expire_hours)


def password_reset_token_expires_at() -> datetime:
    return now_utc() + timedelta(minutes=settings.password_reset_token_expire_minutes)
