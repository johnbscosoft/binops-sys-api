from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class PaymentMethods(BaseModel):
    cash: bool = True
    mobile_money: bool = True
    bank_transfer: bool = True
    cheque: bool = False


class InvoiceSettingsUpdate(BaseModel):
    invoice_prefix: str | None = Field(default=None, min_length=1, max_length=12)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    due_in_days: int | None = Field(default=None, ge=0, le=365)
    payment_methods: PaymentMethods | None = None
    payment_instructions: str | None = Field(default=None, max_length=5000)
    terms_and_conditions: str | None = Field(default=None, max_length=10000)
    vat_enabled: bool | None = None
    vat_rate: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    prices_include_vat: bool | None = None
    default_notes: str | None = Field(default=None, max_length=5000)
    reminders_enabled: bool | None = None
    reminder_days_before: int | None = Field(default=None, ge=0, le=365)
    reminder_days_after: int | None = Field(default=None, ge=0, le=365)


class InvoiceLineInput(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    unit_price: Decimal = Field(ge=0, max_digits=14, decimal_places=2)


class InvoiceCreate(BaseModel):
    customer_id: int
    issue_date: date
    due_date: date | None = None
    status: Literal["Draft", "Issued"] = "Draft"
    notes: str | None = Field(default=None, max_length=5000)
    lines: list[InvoiceLineInput] = Field(min_length=1)


class InvoiceUpdate(BaseModel):
    due_date: date | None = None
    status: Literal["Draft", "Issued", "Cancelled"] | None = None
    notes: str | None = Field(default=None, max_length=5000)
    lines: list[InvoiceLineInput] | None = Field(default=None, min_length=1)


class InvoiceGenerationRequest(BaseModel):
    billing_month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    customer_id: int | None = None
    issue_date: date | None = None
