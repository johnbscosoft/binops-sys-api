from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.responses import success_response
from app.core.config import get_settings
from app.database import get_db
from app.features.authentication_settings.models import AuthenticationSettings
from app.features.company.router import find_company_by_code_or_404
from app.features.users.model import (
    EmailVerificationToken,
    PasswordResetToken,
    Role,
    TwoFactorChallenge,
    User,
    UserSession,
)
from app.features.users.schema import (
    AssignRoleRequest,
    ChangePasswordRequest,
    DevTokenResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    ResetPasswordRequest,
    RoleCreate,
    RoleRead,
    TokenPair,
    TwoFactorResendRequest,
    TwoFactorVerifyRequest,
    UserAdminCreate,
    UserCreate,
    UserRead,
    UserStatusUpdate,
    UserUpdate,
    VerifyEmailRequest,
)
from app.features.users.security import (
    access_token_expires_at,
    create_jwt_token,
    create_plain_token,
    hash_password,
    hash_token,
    now_utc,
    otp_expires_at,
    password_reset_token_expires_at,
    refresh_token_expires_at,
    verification_token_expires_at,
    verify_password,
)
from app.features.users.two_factor import (
    OtpDeliveryError,
    deliver_otp,
    generate_otp,
    hash_otp,
    mask_email,
    mask_phone,
    verify_otp,
)

router = APIRouter(tags=["users"])
bearer_scheme = HTTPBearer()
DbSession = Annotated[Session, Depends(get_db)]
settings = get_settings()


def find_user_by_identity(db: Session, *, email: str, username: str | None = None) -> User | None:
    filters = [User.email == email]
    if username:
        filters.append(User.username == username)
    return db.query(User).filter(or_(*filters)).first()


def find_user_or_404(db: Session, user_id: UUID) -> User:
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def find_company_user_or_404(db: Session, user_id: UUID, company_id: UUID) -> User:
    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.company_id == company_id,
            User.deleted_at.is_(None),
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def create_verification_token(db: Session, user: User) -> str:
    plain_token = create_plain_token()
    db.add(
        EmailVerificationToken(
            user_id=user.id,
            token_hash=hash_token(plain_token),
            expires_at=verification_token_expires_at(),
        )
    )
    return plain_token


def create_session(db: Session, user: User, request: Request) -> TokenPair:
    access_expires_at = access_token_expires_at()
    access_token = create_jwt_token(
        {
            "sub": str(user.id),
            "user_id": str(user.id),
            "company_id": str(user.company_id),
            "email": user.email,
            "is_superuser": user.is_superuser,
            "exp": int(access_expires_at.timestamp()),
            "iat": int(now_utc().timestamp()),
            "jti": create_plain_token(),
        }
    )
    refresh_token = create_plain_token()

    db.add(
        UserSession(
            user_id=user.id,
            access_token_hash=hash_token(access_token),
            refresh_token_hash=hash_token(refresh_token),
            expires_at=access_expires_at,
            refresh_expires_at=refresh_token_expires_at(),
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    )
    user.last_login_at = now_utc()
    db.commit()

    return TokenPair(access_token=access_token, refresh_token=refresh_token)


def create_two_factor_challenge(
    db: Session,
    user: User,
    *,
    allow_email: bool = True,
    allow_sms: bool = True,
) -> tuple[TwoFactorChallenge, str | None]:
    now = now_utc()
    db.query(TwoFactorChallenge).filter(
        TwoFactorChallenge.user_id == user.id,
        TwoFactorChallenge.used_at.is_(None),
    ).update({"used_at": now})

    challenge = TwoFactorChallenge(
        user_id=user.id,
        otp_hash="pending",
        delivery_channels="pending",
        attempt_count=0,
        max_attempts=settings.otp_max_attempts,
        expires_at=otp_expires_at(),
        last_sent_at=now,
    )
    db.add(challenge)
    db.flush()

    otp = generate_otp()
    challenge.otp_hash = hash_otp(challenge.id, otp)
    try:
        delivery = deliver_otp(
            user,
            otp,
            allow_email=allow_email,
            allow_sms=allow_sms,
        )
    except OtpDeliveryError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    challenge.delivery_channels = ",".join(delivery.channels)
    db.commit()
    db.refresh(challenge)
    return challenge, delivery.development_otp


def two_factor_response(
    challenge: TwoFactorChallenge,
    development_otp: str | None = None,
) -> dict[str, object]:
    now = now_utc()
    return {
        "requires_two_factor": True,
        "challenge_id": challenge.id,
        "masked_email": mask_email(challenge.user.email),
        "masked_phone": mask_phone(challenge.user.phone_number),
        "delivery_channels": challenge.delivery_channels.split(","),
        "expires_in_seconds": max(0, int((challenge.expires_at - now).total_seconds())),
        "resend_available_in_seconds": max(
            0,
            settings.otp_resend_cooldown_seconds
            - int((now - challenge.last_sent_at).total_seconds()),
        ),
        "development_otp": development_otp,
    }


def get_current_session(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: DbSession,
) -> UserSession:
    session = (
        db.query(UserSession)
        .filter(
            UserSession.access_token_hash == hash_token(credentials.credentials),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now_utc(),
        )
        .first()
    )

    if not session or session.user.deleted_at is not None or not session.user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    return session


def get_current_user(
    session: Annotated[UserSession, Depends(get_current_session)],
) -> User:
    return session.user


def require_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required",
        )
    return current_user


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserCreate, db: DbSession) -> dict[str, object]:
    company = find_company_by_code_or_404(db, user_data.company_code)

    if find_user_by_identity(db, email=user_data.email, username=user_data.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already exists",
        )

    is_first_company_user = db.query(User).filter(User.company_id == company.id).count() == 0
    user = User(
        company_id=company.id,
        email=user_data.email,
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone_number=user_data.phone_number,
        avatar_url=user_data.avatar_url,
        is_superuser=is_first_company_user,
    )
    db.add(user)
    db.flush()
    verification_token = create_verification_token(db, user)
    db.commit()

    return success_response(
        data={"token": verification_token},
        message="User registered successfully. Verify email before treating the account as trusted.",
    )


@router.post("/auth/login")
def login_user(login: LoginRequest, request: Request, db: DbSession) -> dict[str, object]:
    user = db.query(User).filter(User.email == login.email, User.deleted_at.is_(None)).first()
    if not user or not verify_password(login.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    authentication_settings = (
        db.query(AuthenticationSettings)
        .filter(AuthenticationSettings.company_id == user.company_id)
        .first()
    )
    if authentication_settings and not authentication_settings.otp_enabled:
        return success_response(
            create_session(db, user, request),
            message="Login successful",
        )

    challenge, development_otp = create_two_factor_challenge(
        db,
        user,
        allow_email=(
            authentication_settings.email_otp_enabled
            if authentication_settings
            else True
        ),
        allow_sms=(
            authentication_settings.sms_otp_enabled
            if authentication_settings
            else True
        ),
    )
    return success_response(
        two_factor_response(challenge, development_otp),
        message="Verification code sent",
    )


@router.post("/auth/2fa/verify")
def verify_two_factor(
    verification: TwoFactorVerifyRequest,
    request: Request,
    db: DbSession,
) -> dict[str, object]:
    challenge = (
        db.query(TwoFactorChallenge)
        .filter(TwoFactorChallenge.id == verification.challenge_id)
        .with_for_update()
        .first()
    )
    now = now_utc()
    if not challenge or challenge.used_at is not None or challenge.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code is invalid or expired",
        )
    if challenge.attempt_count >= challenge.max_attempts:
        challenge.used_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many incorrect attempts. Sign in again.",
        )

    if not verify_otp(challenge.id, verification.otp, challenge.otp_hash):
        challenge.attempt_count += 1
        remaining_attempts = challenge.max_attempts - challenge.attempt_count
        if remaining_attempts <= 0:
            challenge.used_at = now
        db.commit()
        detail = (
            "Too many incorrect attempts. Sign in again."
            if remaining_attempts <= 0
            else f"Incorrect verification code. {remaining_attempts} attempts remaining."
        )
        raise HTTPException(
            status_code=(
                status.HTTP_429_TOO_MANY_REQUESTS
                if remaining_attempts <= 0
                else status.HTTP_400_BAD_REQUEST
            ),
            detail=detail,
        )

    challenge.used_at = now
    db.flush()
    return success_response(
        create_session(db, challenge.user, request),
        message="Two-factor verification successful",
    )


@router.post("/auth/2fa/resend")
def resend_two_factor(
    resend: TwoFactorResendRequest,
    db: DbSession,
) -> dict[str, object]:
    challenge = (
        db.query(TwoFactorChallenge)
        .filter(TwoFactorChallenge.id == resend.challenge_id)
        .with_for_update()
        .first()
    )
    now = now_utc()
    if not challenge or challenge.used_at is not None or challenge.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification challenge is invalid or expired. Sign in again.",
        )

    elapsed = int((now - challenge.last_sent_at).total_seconds())
    if elapsed < settings.otp_resend_cooldown_seconds:
        wait_seconds = settings.otp_resend_cooldown_seconds - elapsed
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Please wait {wait_seconds} seconds before requesting another code.",
        )

    authentication_settings = (
        db.query(AuthenticationSettings)
        .filter(AuthenticationSettings.company_id == challenge.user.company_id)
        .first()
    )
    if authentication_settings and not authentication_settings.otp_enabled:
        challenge.used_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="OTP authentication has been disabled. Sign in again.",
        )

    otp = generate_otp()
    try:
        delivery = deliver_otp(
            challenge.user,
            otp,
            allow_email=(
                authentication_settings.email_otp_enabled
                if authentication_settings
                else True
            ),
            allow_sms=(
                authentication_settings.sms_otp_enabled
                if authentication_settings
                else True
            ),
        )
    except OtpDeliveryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    challenge.otp_hash = hash_otp(challenge.id, otp)
    challenge.delivery_channels = ",".join(delivery.channels)
    challenge.attempt_count = 0
    challenge.last_sent_at = now
    challenge.expires_at = now + timedelta(minutes=settings.otp_expire_minutes)
    db.commit()
    db.refresh(challenge)
    return success_response(
        two_factor_response(challenge, delivery.development_otp),
        message="A new verification code was sent",
    )


@router.post("/auth/logout")
def logout_user(
    session: Annotated[UserSession, Depends(get_current_session)],
    db: DbSession,
) -> dict[str, object]:
    session.revoked_at = now_utc()
    db.commit()
    return success_response(message="Logged out successfully")


@router.post("/auth/refresh")
def refresh_session(
    refresh_request: RefreshTokenRequest,
    request: Request,
    db: DbSession,
) -> dict[str, object]:
    session = (
        db.query(UserSession)
        .filter(
            UserSession.refresh_token_hash == hash_token(refresh_request.refresh_token),
            UserSession.revoked_at.is_(None),
            UserSession.refresh_expires_at > now_utc(),
        )
        .first()
    )
    if not session or session.user.deleted_at is not None or not session.user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    session.revoked_at = now_utc()
    return success_response(create_session(db, session.user, request))


@router.post("/auth/change-password")
def change_password(
    password_data: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
) -> dict[str, object]:
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is wrong")

    current_user.hashed_password = hash_password(password_data.new_password)
    db.query(UserSession).filter(UserSession.user_id == current_user.id).update(
        {"revoked_at": now_utc()}
    )
    db.commit()
    return success_response(message="Password changed successfully. Please log in again.")


@router.post("/auth/forgot-password")
def forgot_password(request_data: ForgotPasswordRequest, db: DbSession) -> dict[str, object]:
    user = db.query(User).filter(User.email == request_data.email, User.deleted_at.is_(None)).first()
    if not user:
        return success_response(message="If the account exists, a reset link has been sent.")

    plain_token = create_plain_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(plain_token),
            expires_at=password_reset_token_expires_at(),
        )
    )
    db.commit()
    return success_response(
        data={"token": plain_token},
        message="If the account exists, a reset link has been sent.",
    )


@router.post("/auth/reset-password")
def reset_password(reset_data: ResetPasswordRequest, db: DbSession) -> dict[str, object]:
    reset_token = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == hash_token(reset_data.token),
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now_utc(),
        )
        .first()
    )
    if not reset_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token")

    reset_token.user.hashed_password = hash_password(reset_data.new_password)
    reset_token.used_at = now_utc()
    db.query(UserSession).filter(UserSession.user_id == reset_token.user_id).update(
        {"revoked_at": now_utc()}
    )
    db.commit()
    return success_response(message="Password reset successfully")


@router.post("/auth/verify-email")
def verify_email(verify_data: VerifyEmailRequest, db: DbSession) -> dict[str, object]:
    verification = (
        db.query(EmailVerificationToken)
        .filter(
            EmailVerificationToken.token_hash == hash_token(verify_data.token),
            EmailVerificationToken.used_at.is_(None),
            EmailVerificationToken.expires_at > now_utc(),
        )
        .first()
    )
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    verification.user.is_verified = True
    verification.used_at = now_utc()
    db.commit()
    return success_response(message="Email verified successfully")


@router.post("/auth/resend-verification")
def resend_verification(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
) -> dict[str, object]:
    if current_user.is_verified:
        return success_response(message="Email is already verified")

    token = create_verification_token(db, current_user)
    db.commit()
    return success_response(data={"token": token}, message="Verification token created")


@router.get("/users/me")
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> dict[str, object]:
    return success_response(current_user)


@router.patch("/users/me")
def update_me(
    user_data: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
) -> dict[str, object]:
    updates = user_data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return success_response(current_user)


@router.get("/users/health")
def users_health_check() -> dict[str, object]:
    return success_response(message="users feature ready")


@router.post("/users", status_code=status.HTTP_201_CREATED)
def admin_create_user(
    user_data: UserAdminCreate,
    current_user: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> dict[str, object]:
    if find_user_by_identity(db, email=user_data.email, username=user_data.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already exists",
        )

    user = User(
        company_id=current_user.company_id,
        email=user_data.email,
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone_number=user_data.phone_number,
        avatar_url=user_data.avatar_url,
        is_active=user_data.is_active,
        is_verified=user_data.is_verified,
        is_superuser=user_data.is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return success_response(user)


@router.get("/users")
def list_users(
    current_user: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> dict[str, object]:
    users = (
        db.query(User)
        .filter(User.company_id == current_user.company_id, User.deleted_at.is_(None))
        .order_by(User.created_at.desc())
        .all()
    )
    return success_response(users)


@router.get("/users/{user_id}")
def get_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> dict[str, object]:
    return success_response(find_company_user_or_404(db, user_id, current_user.company_id))


@router.patch("/users/{user_id}")
def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    current_user: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> dict[str, object]:
    user = find_company_user_or_404(db, user_id, current_user.company_id)
    for field, value in user_data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return success_response(user)


@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: UUID,
    status_data: UserStatusUpdate,
    current_user: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> dict[str, object]:
    user = find_company_user_or_404(db, user_id, current_user.company_id)
    for field, value in status_data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return success_response(user)


@router.delete("/users/{user_id}")
def soft_delete_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> dict[str, object]:
    user = find_company_user_or_404(db, user_id, current_user.company_id)
    user.deleted_at = now_utc()
    user.is_active = False
    db.query(UserSession).filter(UserSession.user_id == user.id).update({"revoked_at": now_utc()})
    db.commit()
    return success_response(message="User deleted successfully")


@router.delete("/users/{user_id}/hard-delete")
def permanently_delete_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> dict[str, object]:
    user = find_company_user_or_404(db, user_id, current_user.company_id)
    db.delete(user)
    db.commit()
    return success_response(message="User permanently deleted")


@router.post("/users/{user_id}/revoke-sessions")
def revoke_user_sessions(
    user_id: UUID,
    current_user: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> dict[str, object]:
    user = find_company_user_or_404(db, user_id, current_user.company_id)
    db.query(UserSession).filter(UserSession.user_id == user.id).update({"revoked_at": now_utc()})
    db.commit()
    return success_response(message="User sessions revoked")


@router.post("/roles", status_code=status.HTTP_201_CREATED)
def create_role(
    role_data: RoleCreate,
    current_user: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> dict[str, object]:
    existing_role = (
        db.query(Role)
        .filter(Role.company_id == current_user.company_id, Role.name == role_data.name)
        .first()
    )
    if existing_role:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role already exists")

    role = Role(
        company_id=current_user.company_id,
        name=role_data.name,
        description=role_data.description,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return success_response(role)


@router.get("/roles")
def list_roles(
    current_user: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> dict[str, object]:
    roles = (
        db.query(Role)
        .filter(Role.company_id == current_user.company_id)
        .order_by(Role.name.asc())
        .all()
    )
    return success_response(roles)


@router.post("/users/{user_id}/roles")
def assign_role(
    user_id: UUID,
    role_data: AssignRoleRequest,
    current_user: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> dict[str, object]:
    user = find_user_or_404(db, user_id)
    if user.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot assign roles to users from another company",
        )

    role = (
        db.query(Role)
        .filter(Role.company_id == current_user.company_id, Role.name == role_data.role_name)
        .first()
    )
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    if role not in user.roles:
        user.roles.append(role)
    db.commit()
    db.refresh(user)
    return success_response(user)


@router.get("/users/{user_id}/roles")
def list_user_roles(
    user_id: UUID,
    current_user: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> dict[str, object]:
    return success_response(find_company_user_or_404(db, user_id, current_user.company_id).roles)


@router.delete("/users/{user_id}/roles/{role_name}")
def remove_role(
    user_id: UUID,
    role_name: str,
    current_user: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> dict[str, object]:
    user = find_company_user_or_404(db, user_id, current_user.company_id)
    user.roles = [
        role
        for role in user.roles
        if not (role.company_id == current_user.company_id and role.name == role_name)
    ]
    db.commit()
    db.refresh(user)
    return success_response(user)
