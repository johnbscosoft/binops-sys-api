from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class StaffPayload(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    employment_date: date | None = None
    designation: str = Field(min_length=2, max_length=100)
    phone_number: str | None = Field(default=None, max_length=40)
    residence: str | None = Field(default=None, max_length=500)
    permit_number: str | None = Field(default=None, max_length=100)
    permit_expiry_date: date | None = None
    date_of_birth: date | None = None
    gender: Literal["Male", "Female"] | None = None
    attachment_name: str | None = Field(default=None, max_length=255)
    attachment_data: str | None = None
    status: Literal["Active", "Inactive"] = "Active"
