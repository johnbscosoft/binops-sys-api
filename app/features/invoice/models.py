import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class InvoiceSettings(Base):
    __tablename__ = "invoice_settings"
    __table_args__ = (UniqueConstraint("company_id", name="uq_invoice_settings_company_id"),)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_prefix = Column(String(12), nullable=False, default="INV", server_default="INV")
    currency = Column(String(3), nullable=False, default="UGX", server_default="UGX")
    due_in_days = Column(Integer, nullable=False, default=7, server_default="7")
    payment_methods = Column(JSONB, nullable=False, default=dict, server_default="{}")
    payment_instructions = Column(Text, nullable=True)
    terms_and_conditions = Column(Text, nullable=True)
    vat_enabled = Column(Boolean, nullable=False, default=False, server_default="false")
    vat_rate = Column(Numeric(5, 2), nullable=False, default=0, server_default="0")
    prices_include_vat = Column(Boolean, nullable=False, default=False, server_default="false")
    default_notes = Column(Text, nullable=True)
    reminders_enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    reminder_days_before = Column(Integer, nullable=False, default=3, server_default="3")
    reminder_days_after = Column(Integer, nullable=False, default=7, server_default="7")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class InvoiceNumberSequence(Base):
    __tablename__ = "invoice_number_sequences"
    __table_args__ = (UniqueConstraint("company_id", "period", name="uq_invoice_number_sequence_company_period"),)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    period = Column(String(6), nullable=False)
    next_number = Column(Integer, nullable=False, default=1, server_default="1")


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("company_id", "invoice_number", name="uq_invoices_company_number"),
        CheckConstraint("status IN ('Draft', 'Issued', 'Partially Paid', 'Paid', 'Overdue', 'Cancelled')", name="ck_invoices_status"),
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_number = Column(String(40), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False, index=True)
    customer_name = Column(String(160), nullable=False)
    customer_code = Column(String(40), nullable=False)
    customer_email = Column(String(255), nullable=True)
    billing_address = Column(String(500), nullable=True)
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(String(30), nullable=False, default="Draft", server_default="Draft", index=True)
    currency = Column(String(3), nullable=False)
    vat_enabled = Column(Boolean, nullable=False, default=False)
    vat_rate = Column(Numeric(5, 2), nullable=False, default=0)
    prices_include_vat = Column(Boolean, nullable=False, default=False)
    subtotal = Column(Numeric(14, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(14, 2), nullable=False, default=0)
    total_amount = Column(Numeric(14, 2), nullable=False, default=0)
    payment_instructions = Column(Text, nullable=True)
    terms_and_conditions = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(String(255), nullable=True)
    updated_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_billing_record_id = Column(UUID(as_uuid=True), ForeignKey("collection_billing_records.id", ondelete="SET NULL"), nullable=True, unique=True)
    description = Column(Text, nullable=False)
    quantity = Column(Numeric(14, 2), nullable=False)
    unit_price = Column(Numeric(14, 2), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
