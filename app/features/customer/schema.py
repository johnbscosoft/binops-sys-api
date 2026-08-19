
from decimal import Decimal
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerRoomInput(BaseModel):
    id: UUID | None = None
    occupant_customer_id: int | None = None
    room_number: str = Field(min_length=1, max_length=80)
    occupancy_status: Literal["Occupied", "Vacant"] = "Vacant"
    occupant_name: str | None = Field(default=None, max_length=160)
    phone_number: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=255)
    subscription_plan_id: UUID | None = None
    price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    number_of_bags: int = Field(default=0, ge=0, strict=True)
    uses_default_pricing: bool = True
    account_status: Literal["Active", "Inactive"] = "Active"


class CreateCustomer(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    phone_no: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=255)
    # Apartment and rental customers inherit this value from their property.
    location: str | None = Field(default=None, max_length=500)
    latitude: float | None = None
    longitude: float | None = None
    place_id: str | None = None
    number_of_bags: int = Field(default=0, ge=0, strict=True)
    notes: str | None = Field(default=None, max_length=1000)
    agreed_price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    property_id: UUID | None = None
    property_unit_id: UUID | None = None
    occupancy_start_date: date | None = None
    client_category_id: UUID
    subscription_plan_id: UUID | None = None
    service_arrangement: Literal["LANDLORD", "DIRECT_TENANT"] | None = None
    room_pricing_mode: Literal["SHARED", "PER_ROOM"] | None = None
    caretaker_name: str | None = Field(default=None, max_length=160)
    caretaker_phone: str | None = Field(default=None, max_length=40)
    rooms: list[CustomerRoomInput] = Field(default_factory=list)
    status: str = Field(default="Active", pattern="^(Active|Inactive)$")
    added_by: str | None = None
    updated_by: str | None = None
