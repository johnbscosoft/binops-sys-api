
from uuid import UUID

from pydantic import BaseModel, Field


class CreateCustomer(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    phone_no: str = Field(min_length=10, max_length=40)
    email: str = Field(min_length=3, max_length=255)
    location: str = Field(min_length=2, max_length=500)
    latitude: float | None = None
    longitude: float | None = None
    place_id: str | None = None
    flat_no: str | None = None
    house_no: str | None = None
    subscription_plan_id: UUID
    status: str = Field(default="Active", pattern="^(Active|Inactive)$")
    added_by: str | None = None
    updated_by: str | None = None
