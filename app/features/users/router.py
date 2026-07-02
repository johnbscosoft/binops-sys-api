from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.features.users.model import (
    EmailVerificationToken,
    PasswordResetToken,
    Role,
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
    UserAdminCreate,
    UserCreate,
    UserRead,
    UserStatusUpdate,
    UserUpdate,
    VerifyEmailRequest,
)
from app.features.users.security import (
    access_token_expires_at,
    create_plain_token,
    hash_password,
    hash_token,
    now_utc,
    password_reset_token_expires_at,
    refresh_token_expires_at,
    verification_token_expires_at,
    verify_password,
)

router = APIRouter(tags=["users"])
bearer_scheme = HTTPBearer()
DbSession = Annotated[Session, Depends(get_db)]


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
    access_token = create_plain_token()
    refresh_token = create_plain_token()

    db.add(
        UserSession(
            user_id=user.id,
            access_token_hash=hash_token(access_token),
            refresh_token_hash=hash_token(refresh_token),
            expires_at=access_token_expires_at(),
            refresh_expires_at=refresh_token_expires_at(),
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    )
    user.last_login_at = now_utc()
    db.commit()

    return TokenPair(access_token=access_token, refresh_token=refresh_token)


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


@router.post("/auth/register", response_model=DevTokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserCreate, db: DbSession) -> DevTokenResponse:
    if find_user_by_identity(db, email=user_data.email, username=user_data.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already exists",
        )

    is_first_user = db.query(User).count() == 0
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone_number=user_data.phone_number,
        avatar_url=user_data.avatar_url,
        is_superuser=is_first_user,
    )
    db.add(user)
    db.flush()
    verification_token = create_verification_token(db, user)
    db.commit()

    return DevTokenResponse(
        message="User registered successfully. Verify email before treating the account as trusted.",
        token=verification_token,
    )


@router.post("/auth/login", response_model=TokenPair)
def login_user(login: LoginRequest, request: Request, db: DbSession) -> TokenPair:
    user = db.query(User).filter(User.email == login.email, User.deleted_at.is_(None)).first()
    if not user or not verify_password(login.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    return create_session(db, user, request)


@router.post("/auth/logout", response_model=MessageResponse)
def logout_user(
    session: Annotated[UserSession, Depends(get_current_session)],
    db: DbSession,
) -> MessageResponse:
    session.revoked_at = now_utc()
    db.commit()
    return MessageResponse(message="Logged out successfully")


@router.post("/auth/refresh", response_model=TokenPair)
def refresh_session(
    refresh_request: RefreshTokenRequest,
    request: Request,
    db: DbSession,
) -> TokenPair:
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
    return create_session(db, session.user, request)


@router.post("/auth/change-password", response_model=MessageResponse)
def change_password(
    password_data: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
) -> MessageResponse:
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is wrong")

    current_user.hashed_password = hash_password(password_data.new_password)
    db.query(UserSession).filter(UserSession.user_id == current_user.id).update(
        {"revoked_at": now_utc()}
    )
    db.commit()
    return MessageResponse(message="Password changed successfully. Please log in again.")


@router.post("/auth/forgot-password", response_model=DevTokenResponse)
def forgot_password(request_data: ForgotPasswordRequest, db: DbSession) -> DevTokenResponse:
    user = db.query(User).filter(User.email == request_data.email, User.deleted_at.is_(None)).first()
    if not user:
        return DevTokenResponse(message="If the account exists, a reset link has been sent.")

    plain_token = create_plain_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(plain_token),
            expires_at=password_reset_token_expires_at(),
        )
    )
    db.commit()
    return DevTokenResponse(
        message="If the account exists, a reset link has been sent.",
        token=plain_token,
    )


@router.post("/auth/reset-password", response_model=MessageResponse)
def reset_password(reset_data: ResetPasswordRequest, db: DbSession) -> MessageResponse:
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
    return MessageResponse(message="Password reset successfully")


@router.post("/auth/verify-email", response_model=MessageResponse)
def verify_email(verify_data: VerifyEmailRequest, db: DbSession) -> MessageResponse:
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
    return MessageResponse(message="Email verified successfully")


@router.post("/auth/resend-verification", response_model=DevTokenResponse)
def resend_verification(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
) -> DevTokenResponse:
    if current_user.is_verified:
        return DevTokenResponse(message="Email is already verified")

    token = create_verification_token(db, current_user)
    db.commit()
    return DevTokenResponse(message="Verification token created", token=token)


@router.get("/users/me", response_model=UserRead)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.patch("/users/me", response_model=UserRead)
def update_me(
    user_data: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
) -> User:
    updates = user_data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/users/health", response_model=MessageResponse)
def users_health_check() -> MessageResponse:
    return MessageResponse(message="users feature ready")


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    user_data: UserAdminCreate,
    _: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> User:
    if find_user_by_identity(db, email=user_data.email, username=user_data.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already exists",
        )

    user = User(
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
    return user


@router.get("/users", response_model=list[UserRead])
def list_users(
    _: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> list[User]:
    return db.query(User).filter(User.deleted_at.is_(None)).order_by(User.created_at.desc()).all()


@router.get("/users/{user_id}", response_model=UserRead)
def get_user(
    user_id: UUID,
    _: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> User:
    return find_user_or_404(db, user_id)


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    _: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> User:
    user = find_user_or_404(db, user_id)
    for field, value in user_data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/status", response_model=UserRead)
def update_user_status(
    user_id: UUID,
    status_data: UserStatusUpdate,
    _: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> User:
    user = find_user_or_404(db, user_id)
    for field, value in status_data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", response_model=MessageResponse)
def soft_delete_user(
    user_id: UUID,
    _: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> MessageResponse:
    user = find_user_or_404(db, user_id)
    user.deleted_at = now_utc()
    user.is_active = False
    db.query(UserSession).filter(UserSession.user_id == user.id).update({"revoked_at": now_utc()})
    db.commit()
    return MessageResponse(message="User deleted successfully")


@router.delete("/users/{user_id}/hard-delete", response_model=MessageResponse)
def permanently_delete_user(
    user_id: UUID,
    _: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> MessageResponse:
    user = find_user_or_404(db, user_id)
    db.delete(user)
    db.commit()
    return MessageResponse(message="User permanently deleted")


@router.post("/users/{user_id}/revoke-sessions", response_model=MessageResponse)
def revoke_user_sessions(
    user_id: UUID,
    _: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> MessageResponse:
    user = find_user_or_404(db, user_id)
    db.query(UserSession).filter(UserSession.user_id == user.id).update({"revoked_at": now_utc()})
    db.commit()
    return MessageResponse(message="User sessions revoked")


@router.post("/roles", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
def create_role(
    role_data: RoleCreate,
    _: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> Role:
    existing_role = db.query(Role).filter(Role.name == role_data.name).first()
    if existing_role:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role already exists")

    role = Role(name=role_data.name, description=role_data.description)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.get("/roles", response_model=list[RoleRead])
def list_roles(
    _: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> list[Role]:
    return db.query(Role).order_by(Role.name.asc()).all()


@router.post("/users/{user_id}/roles", response_model=UserRead)
def assign_role(
    user_id: UUID,
    role_data: AssignRoleRequest,
    _: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> User:
    user = find_user_or_404(db, user_id)
    role = db.query(Role).filter(Role.name == role_data.role_name).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    if role not in user.roles:
        user.roles.append(role)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users/{user_id}/roles", response_model=list[RoleRead])
def list_user_roles(
    user_id: UUID,
    _: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> list[Role]:
    return find_user_or_404(db, user_id).roles


@router.delete("/users/{user_id}/roles/{role_name}", response_model=UserRead)
def remove_role(
    user_id: UUID,
    role_name: str,
    _: Annotated[User, Depends(require_superuser)],
    db: DbSession,
) -> User:
    user = find_user_or_404(db, user_id)
    user.roles = [role for role in user.roles if role.name != role_name]
    db.commit()
    db.refresh(user)
    return user
