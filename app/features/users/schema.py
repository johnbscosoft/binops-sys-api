from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str | None = None


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    description: str | None


# Request schema for creating a user. The password should be hashed before
# saving it to User.hashed_password.
class UserCreate(BaseModel):
    company_code: str = Field(min_length=7, max_length=7)
    email: EmailStr
    password: str = Field(min_length=8)
    username: str | None = Field(default=None, max_length=80)
    first_name: str | None = Field(default=None, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    phone_number: str | None = Field(default=None, max_length=40)
    avatar_url: str | None = None


class UserAdminCreate(UserCreate):
    company_code: str | None = Field(default=None, min_length=7, max_length=7)
    is_active: bool = True
    is_verified: bool = False
    is_superuser: bool = False


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = Field(default=None, max_length=80)
    first_name: str | None = Field(default=None, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    phone_number: str | None = Field(default=None, max_length=40)
    avatar_url: str | None = None


class UserStatusUpdate(BaseModel):
    is_active: bool | None = None
    is_verified: bool | None = None
    is_superuser: bool | None = None


class UserRead(BaseModel):
    # Public response schema. Notice password fields are intentionally excluded.
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    email: EmailStr
    username: str | None
    first_name: str | None
    last_name: str | None
    phone_number: str | None
    avatar_url: str | None
    is_active: bool
    is_verified: bool
    is_superuser: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    roles: list[RoleRead] = []


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TwoFactorVerifyRequest(BaseModel):
    challenge_id: UUID
    otp: str = Field(pattern=r"^\d{6}$")


class TwoFactorResendRequest(BaseModel):
    challenge_id: UUID


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class VerifyEmailRequest(BaseModel):
    token: str


class AssignRoleRequest(BaseModel):
    role_name: str


class MessageResponse(BaseModel):
    message: str


class DevTokenResponse(MessageResponse):
    # In a real production app, this token is emailed instead of returned.
    token: str | None = None
