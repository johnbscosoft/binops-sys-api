
from pydantic import BaseModel, Field


class CreateCustomer(BaseModel):
    name: str
    phone_no: str
    email: str
    location: str
    subscription_type: str
    contract_amount: float = Field(gt=0)
    added_by: str | None = None
    updated_by: str | None = None
