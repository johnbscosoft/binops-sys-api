from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CompanyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    phone_number: str = Field(min_length=3, max_length=12)
    logo: str | None = None
    contact_person: str = Field(min_length=2, max_length=160)


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    email: EmailStr | None = None
    phone_number: str | None = Field(default=None, min_length=3, max_length=40)
    logo: str | None = None
    contact_person: str | None = Field(default=None, min_length=2, max_length=160)


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_code: str
    name: str
    email: EmailStr
    phone_number: str
    logo: str | None
    contact_person: str
    created_at: datetime
    updated_at: datetime
