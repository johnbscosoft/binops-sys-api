import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel

# Loads values from a local .env file into os.environ during development.
load_dotenv()


# Application settings are centralized here so secrets and environment-specific
# values are not hardcoded throughout the codebase.
class Settings(BaseModel):
    app_name: str = "WasteOps Sys API"
    api_v1_prefix: str = "/api/v1"
    environment: str = os.getenv("ENVIRONMENT", "development")

    # Helpful during early development. In production, prefer Alembic migrations
    # and set AUTO_CREATE_TABLES=false.
    auto_create_tables: bool = os.getenv("AUTO_CREATE_TABLES", "true").lower() == "true"

    # Override with DATABASE_URL in .env or the deployment environment.
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://admin:admin123@localhost:5432/wasteops_db",
    )
    cors_origins: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:4200,http://127.0.0.1:4200",
        ).split(",")
        if origin.strip()
    ]

    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")

    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    verification_token_expire_hours: int = int(
        os.getenv("VERIFICATION_TOKEN_EXPIRE_HOURS", "24")
    )
    password_reset_token_expire_minutes: int = int(
        os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "30")
    )

    otp_expire_minutes: int = int(os.getenv("OTP_EXPIRE_MINUTES", "5"))
    otp_max_attempts: int = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
    otp_resend_cooldown_seconds: int = int(
        os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60")
    )
    otp_development_mode: bool = os.getenv(
        "OTP_DEVELOPMENT_MODE",
        "true" if os.getenv("ENVIRONMENT", "development").lower() != "production" else "false",
    ).lower() == "true"

    smtp_host: str | None = os.getenv("SMTP_HOST")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str | None = os.getenv("SMTP_USERNAME")
    smtp_password: str | None = os.getenv("SMTP_PASSWORD")
    smtp_from_email: str | None = os.getenv("SMTP_FROM_EMAIL")
    smtp_use_tls: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    smtp_use_ssl: bool = os.getenv("SMTP_USE_SSL", "false").lower() == "true"

    twilio_account_sid: str | None = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_auth_token: str | None = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_from_number: str | None = os.getenv("TWILIO_FROM_NUMBER")
    sms_default_country_code: str = os.getenv("SMS_DEFAULT_COUNTRY_CODE", "+256")


@lru_cache
def get_settings() -> Settings:
    # Cache settings so every import uses the same config instance.
    return Settings()
