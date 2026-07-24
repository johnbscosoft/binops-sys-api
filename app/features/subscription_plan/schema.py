from decimal import Decimal

from pydantic import BaseModel, Field


class SubscriptionPlanCreate(BaseModel):
    duration: str = Field(min_length=2, max_length=80)
    pickup_frequency: str = Field(min_length=2, max_length=80)
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    notes: str | None = Field(default=None, max_length=500)
    is_custom: bool = False
    is_active: bool = True


class SubscriptionPlanUpdate(BaseModel):
    duration: str | None = Field(default=None, min_length=2, max_length=80)
    pickup_frequency: str | None = Field(default=None, min_length=2, max_length=80)
    amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    notes: str | None = Field(default=None, max_length=500)
    is_custom: bool | None = None
    is_active: bool | None = None
