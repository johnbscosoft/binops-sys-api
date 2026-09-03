from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.responses import success_response
from app.core.config import get_settings
from app.database import get_db
from app.features.authentication_settings.models import AuthenticationSettings
from app.features.authentication_settings.schema import AuthenticationSettingsUpdate
from app.features.users.model import User
from app.features.users.router import get_current_user, require_superuser

router = APIRouter(prefix="/authentication-settings", tags=["authentication settings"])
DbSession = Annotated[Session, Depends(get_db)]
Superuser = Annotated[User, Depends(require_superuser)]
CurrentUser = Annotated[User, Depends(get_current_user)]
app_settings = get_settings()


def find_or_create_settings(db: Session, company_id) -> AuthenticationSettings:
    settings = (
        db.query(AuthenticationSettings)
        .filter(AuthenticationSettings.company_id == company_id)
        .first()
    )
    if settings:
        return settings

    settings = AuthenticationSettings(company_id=company_id)
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def settings_response(settings: AuthenticationSettings) -> dict[str, object]:
    return {
        "id": settings.id,
        "company_id": settings.company_id,
        "otp_enabled": settings.otp_enabled,
        "email_otp_enabled": settings.email_otp_enabled,
        "sms_otp_enabled": settings.sms_otp_enabled,
        "google_location_enabled": settings.google_location_enabled,
        "location_provider": settings.location_provider,
        "email_delivery_configured": bool(
            app_settings.smtp_host and app_settings.smtp_from_email
        ),
        "sms_delivery_configured": bool(
            app_settings.twilio_account_sid
            and app_settings.twilio_auth_token
            and app_settings.twilio_from_number
        ),
        "development_mode": app_settings.otp_development_mode,
        "updated_at": settings.updated_at,
    }


@router.get("")
def get_authentication_settings(
    current_user: Superuser,
    db: DbSession,
) -> dict[str, object]:
    return success_response(
        settings_response(find_or_create_settings(db, current_user.company_id))
    )


@router.patch("")
def update_authentication_settings(
    settings_data: AuthenticationSettingsUpdate,
    current_user: Superuser,
    db: DbSession,
) -> dict[str, object]:
    settings = find_or_create_settings(db, current_user.company_id)
    values = settings_data.model_dump()
    values["google_location_enabled"] = values["location_provider"] == "GOOGLE"
    for field, value in values.items():
        setattr(settings, field, value)
    db.commit()
    db.refresh(settings)
    return success_response(
        settings_response(settings),
        message="Authentication settings updated successfully",
    )


@router.get("/location")
def get_location_settings(
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, object]:
    settings = find_or_create_settings(db, current_user.company_id)
    return success_response({"location_provider": settings.location_provider})
