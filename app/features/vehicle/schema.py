from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class VehiclePayload(BaseModel):
    plate_number: str = Field(min_length=2, max_length=40)
    model: str = Field(min_length=2, max_length=160)
    driver_id: UUID | None = None
    status: Literal["Active", "Inactive"] = "Active"
