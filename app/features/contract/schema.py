from datetime import date

from pydantic import BaseModel, model_validator


class CustomerContractCreate(BaseModel):
    customer_id: int
    start_date: date
    expiry_date: date | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.expiry_date is not None and self.expiry_date <= self.start_date:
            raise ValueError("Expiry date must be after the start date")
        return self
