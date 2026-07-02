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

    # Helpful during early development. In production, prefer Alembic migrations
    # and set AUTO_CREATE_TABLES=false.
    auto_create_tables: bool = os.getenv("AUTO_CREATE_TABLES", "true").lower() == "true"

    # Override with DATABASE_URL in .env or the deployment environment.
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://admin:admin123@localhost:5432/wasteops_db",
    )

    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    verification_token_expire_hours: int = int(
        os.getenv("VERIFICATION_TOKEN_EXPIRE_HOURS", "24")
    )
    password_reset_token_expire_minutes: int = int(
        os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "30")
    )


@lru_cache
def get_settings() -> Settings:
    # Cache settings so every import uses the same config instance.
    return Settings()
