from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class VehiclePayload(BaseModel):
    plate_number: str = Field(min_length=2, max_length=40)
    model: str = Field(min_length=2, max_length=160)
    chassis_number: str | None = Field(default=None, max_length=100)
    vehicle_type: str | None = Field(default=None, max_length=100)
    purchase_date: date | None = None
    third_party_insurance_expiry: date | None = None
    truck_photo_name: str | None = Field(default=None, max_length=255)
    truck_photo_data: str | None = None
    logbook_name: str | None = Field(default=None, max_length=255)
    logbook_data: str | None = None
    driver_id: UUID | None = None
    status: Literal["Active", "Inactive"] = "Active"
