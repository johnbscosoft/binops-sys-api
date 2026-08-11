from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class PropertyUnitInput(BaseModel):
    id: UUID | None = None
    room_number: str = Field(min_length=1, max_length=80)
    is_active: bool = True
    occupancy_status: Literal["Occupied", "Vacant"] = "Vacant"


class PropertyPayload(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    property_type: Literal["APARTMENT", "RENTAL"]
    billing_mode: Literal["OWNER", "TENANT"]
    owner_customer_id: int | None = None
    owner_name: str | None = Field(default=None, max_length=160)
    owner_phone_number: str | None = Field(default=None, max_length=40)
    owner_email: str | None = Field(default=None, max_length=255)
    subscription_plan_id: UUID | None = None
    location: str = Field(min_length=2, max_length=500)
    status: Literal["Active", "Inactive"] = "Active"
    units: list[PropertyUnitInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_owner_billing(self):
        if self.billing_mode == "OWNER":
            if not self.owner_name or len(self.owner_name.strip()) < 2:
                raise ValueError("Property owner name is required when the owner pays")
            phone = (self.owner_phone_number or "").strip()
            if len(phone) != 10 or not phone.startswith("07") or not phone.isdigit():
                raise ValueError("A valid property owner phone number is required")
            email = (self.owner_email or "").strip()
            if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
                raise ValueError("A valid property owner email is required")
            if self.subscription_plan_id is None:
                raise ValueError("Property subscription plan is required when the owner pays")
        return self
