from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CollectionAreaPayload(BaseModel):
    area_code: str | None = Field(default=None, max_length=40)
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=500)
    latitude: float | None = None
    longitude: float | None = None
    place_id: str | None = Field(default=None, max_length=255)
    service_model: Literal["DIRECT", "SUBCONTRACT"] = "DIRECT"
    contracting_organisation_id: UUID | None = None
    status: Literal["Active", "Inactive"] = "Active"

    @field_validator("area_code", "name", mode="before")
    @classmethod
    def normalize_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.strip().split())
        return normalized or None


class CollectionRoutePayload(BaseModel):
    area_id: UUID
    area_code: str = Field(min_length=2, max_length=40)
    route_code: str | None = Field(default=None, min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=160)
    vehicle_id: UUID | None = None
    status: Literal["Active", "Inactive"] = "Active"

    @field_validator("area_code", "name", mode="before")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        return " ".join(value.strip().split())


class ContractingOrganisationPayload(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    commission_type: Literal[
        "PERCENTAGE_OF_LUMP_SUM",
        "PERCENTAGE_PER_COLLECTION",
        "FIXED_AMOUNT_OF_LUMP_SUM",
        "FIXED_AMOUNT_PER_COLLECTION",
    ]
    commission_rate: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    contract_start_date: date | None = None
    contract_end_date: date | None = None
