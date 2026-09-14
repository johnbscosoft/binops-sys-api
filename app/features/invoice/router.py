from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.responses import success_response
from app.database import get_db
from app.features.customer.models import Customer
from app.features.collection_billing.models import CollectionBillingRecord
from app.features.invoice.models import Invoice, InvoiceLine, InvoiceNumberSequence, InvoiceSettings
from app.features.invoice.schema import InvoiceCreate, InvoiceGenerationRequest, InvoiceLineInput, InvoiceSettingsUpdate, InvoiceUpdate
from app.features.users.model import User
from app.features.users.router import get_current_user

router = APIRouter(tags=["invoices"])
Db = Annotated[Session, Depends(get_db)]
Current = Annotated[User, Depends(get_current_user)]
MONEY = Decimal("0.01")


def settings_for_company(db: Session, company_id) -> InvoiceSettings:
    settings = db.query(InvoiceSettings).filter_by(company_id=company_id).first()
    if settings:
        return settings
    settings = InvoiceSettings(company_id=company_id, payment_methods={"cash": True, "mobile_money": True, "bank_transfer": True, "cheque": False})
    db.add(settings)
    db.flush()
    return settings


def serialize_settings(settings: InvoiceSettings) -> dict:
    return {"invoice_prefix": settings.invoice_prefix, "currency": settings.currency, "due_in_days": settings.due_in_days, "payment_methods": settings.payment_methods or {}, "payment_instructions": settings.payment_instructions, "terms_and_conditions": settings.terms_and_conditions, "vat_enabled": settings.vat_enabled, "vat_rate": settings.vat_rate, "prices_include_vat": settings.prices_include_vat, "default_notes": settings.default_notes, "reminders_enabled": settings.reminders_enabled, "reminder_days_before": settings.reminder_days_before, "reminder_days_after": settings.reminder_days_after}


def invoice_lines(db: Session, invoice_id: UUID) -> list[InvoiceLine]:
    return db.query(InvoiceLine).filter_by(invoice_id=invoice_id).order_by(InvoiceLine.created_at).all()


def serialize_invoice(invoice: Invoice, db: Session) -> dict:
    lines = invoice_lines(db, invoice.id)
    return {"id": invoice.id, "invoice_number": invoice.invoice_number, "customer_id": invoice.customer_id, "customer": invoice.customer_name, "customer_code": invoice.customer_code, "customer_email": invoice.customer_email, "customer_location": invoice.billing_address, "issue_date": invoice.issue_date, "due_date": invoice.due_date, "status": invoice.status, "currency": invoice.currency, "vat_enabled": invoice.vat_enabled, "vat_rate": invoice.vat_rate, "prices_include_vat": invoice.prices_include_vat, "subtotal": invoice.subtotal, "tax_amount": invoice.tax_amount, "total_amount": invoice.total_amount, "payment_instructions": invoice.payment_instructions, "terms_and_conditions": invoice.terms_and_conditions, "notes": invoice.notes, "lines": [{"id": line.id, "description": line.description, "quantity": line.quantity, "unit_price": line.unit_price, "amount": line.amount} for line in lines], "created_at": invoice.created_at, "updated_at": invoice.updated_at}


def next_invoice_number(db: Session, company_id, issue_date: date, prefix: str) -> str:
    period = issue_date.strftime("%Y%m")
    sequence = db.query(InvoiceNumberSequence).filter_by(company_id=company_id, period=period).with_for_update().first()
    if not sequence:
        sequence = InvoiceNumberSequence(company_id=company_id, period=period, next_number=1)
        db.add(sequence)
        db.flush()
    number = sequence.next_number
    sequence.next_number += 1
    return f"{prefix.strip().upper() or 'INV'}-{period}-{number:06d}"


def calculate(lines, settings: InvoiceSettings) -> tuple[Decimal, Decimal, Decimal]:
    subtotal = sum((line.quantity * line.unit_price for line in lines), Decimal("0")).quantize(MONEY, rounding=ROUND_HALF_UP)
    tax = Decimal("0")
    if settings.vat_enabled and settings.vat_rate:
        rate = Decimal(settings.vat_rate) / Decimal("100")
        tax = (subtotal - subtotal / (Decimal("1") + rate) if settings.prices_include_vat else subtotal * rate).quantize(MONEY, rounding=ROUND_HALF_UP)
    total = subtotal if settings.prices_include_vat else (subtotal + tax).quantize(MONEY, rounding=ROUND_HALF_UP)
    return subtotal, tax, total


def replace_lines(db: Session, invoice: Invoice, inputs, settings: InvoiceSettings) -> None:
    db.query(InvoiceLine).filter_by(invoice_id=invoice.id).delete(synchronize_session=False)
    subtotal, tax, total = calculate(inputs, settings)
    for input_line in inputs:
        amount = (input_line.quantity * input_line.unit_price).quantize(MONEY, rounding=ROUND_HALF_UP)
        db.add(InvoiceLine(invoice_id=invoice.id, description=input_line.description.strip(), quantity=input_line.quantity, unit_price=input_line.unit_price, amount=amount))
    invoice.subtotal, invoice.tax_amount, invoice.total_amount = subtotal, tax, total


def find_invoice(db: Session, invoice_id: UUID, company_id) -> Invoice:
    invoice = db.query(Invoice).filter_by(id=invoice_id, company_id=company_id).first()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    return invoice


@router.get("/invoice-settings")
def get_invoice_settings(user: Current, db: Db):
    settings = settings_for_company(db, user.company_id)
    db.commit(); db.refresh(settings)
    return success_response(serialize_settings(settings))


@router.patch("/invoice-settings")
def update_invoice_settings(payload: InvoiceSettingsUpdate, user: Current, db: Db):
    settings = settings_for_company(db, user.company_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, key, value)
    db.commit(); db.refresh(settings)
    return success_response(serialize_settings(settings), message="Invoice settings updated successfully")


@router.get("/invoices")
def list_invoices(user: Current, db: Db, status: str | None = None):
    query = db.query(Invoice).filter_by(company_id=user.company_id)
    if status: query = query.filter(Invoice.status == status)
    return success_response([serialize_invoice(invoice, db) for invoice in query.order_by(Invoice.issue_date.desc(), Invoice.created_at.desc()).all()])


@router.post("/invoices", status_code=201)
def create_invoice(payload: InvoiceCreate, user: Current, db: Db):
    customer = db.query(Customer).filter_by(id=payload.customer_id, company_id=user.company_id).first()
    if not customer: raise HTTPException(422, "Select a valid customer")
    settings = settings_for_company(db, user.company_id)
    invoice = Invoice(company_id=user.company_id, invoice_number=next_invoice_number(db, user.company_id, payload.issue_date, settings.invoice_prefix), customer_id=customer.id, customer_name=customer.name, customer_code=f"CUST-{customer.id:04d}", customer_email=customer.email, billing_address=customer.location, issue_date=payload.issue_date, due_date=payload.due_date or payload.issue_date + timedelta(days=settings.due_in_days), status=payload.status, currency=settings.currency, vat_enabled=settings.vat_enabled, vat_rate=settings.vat_rate, prices_include_vat=settings.prices_include_vat, payment_instructions=settings.payment_instructions, terms_and_conditions=settings.terms_and_conditions, notes=payload.notes if payload.notes is not None else settings.default_notes, created_by=user.email, updated_by=user.email)
    db.add(invoice); db.flush(); replace_lines(db, invoice, payload.lines, settings); db.commit(); db.refresh(invoice)
    return success_response(serialize_invoice(invoice, db), message="Invoice created successfully")


@router.post("/invoices/generate-drafts")
def generate_draft_invoices(payload: InvoiceGenerationRequest, user: Current, db: Db):
    query = db.query(CollectionBillingRecord).filter_by(company_id=user.company_id, billing_month=payload.billing_month, billing_status="Unbilled", invoice_id=None)
    if payload.customer_id is not None:
        query = query.filter(CollectionBillingRecord.customer_id == payload.customer_id)
    records = query.order_by(CollectionBillingRecord.customer_id, CollectionBillingRecord.pickup_date, CollectionBillingRecord.created_at).all()
    if not records:
        return success_response([], message="No unbilled collections were found for this billing month")
    settings = settings_for_company(db, user.company_id)
    issue_date = payload.issue_date or date.today()
    generated: list[Invoice] = []
    by_customer: dict[int, list[CollectionBillingRecord]] = {}
    for record in records:
        by_customer.setdefault(record.customer_id, []).append(record)
    for customer_id, customer_records in by_customer.items():
        customer = db.query(Customer).filter_by(id=customer_id, company_id=user.company_id).first()
        if not customer:
            continue
        invoice = Invoice(company_id=user.company_id, invoice_number=next_invoice_number(db, user.company_id, issue_date, settings.invoice_prefix), customer_id=customer.id, customer_name=customer.name, customer_code=f"CUST-{customer.id:04d}", customer_email=customer.email, billing_address=customer.location, issue_date=issue_date, due_date=issue_date + timedelta(days=settings.due_in_days), status="Draft", currency=settings.currency, vat_enabled=settings.vat_enabled, vat_rate=settings.vat_rate, prices_include_vat=settings.prices_include_vat, payment_instructions=settings.payment_instructions, terms_and_conditions=settings.terms_and_conditions, notes=settings.default_notes, created_by=user.email, updated_by=user.email)
        db.add(invoice); db.flush()
        lines = [InvoiceLineInput(description=record.description, quantity=Decimal("1"), unit_price=record.calculated_amount) for record in customer_records]
        replace_lines(db, invoice, lines, settings)
        db.flush()
        created_lines = invoice_lines(db, invoice.id)
        for record, line in zip(customer_records, created_lines):
            line.collection_billing_record_id = record.id
            record.invoice_id = invoice.id
            record.billing_status = "Draft Invoice"
            record.updated_by = user.email
        generated.append(invoice)
    db.commit()
    return success_response([serialize_invoice(invoice, db) for invoice in generated], message=f"Created {len(generated)} draft invoice(s)")


@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: UUID, user: Current, db: Db):
    return success_response(serialize_invoice(find_invoice(db, invoice_id, user.company_id), db))


@router.put("/invoices/{invoice_id}")
def update_invoice(invoice_id: UUID, payload: InvoiceUpdate, user: Current, db: Db):
    invoice = find_invoice(db, invoice_id, user.company_id)
    if invoice.status not in ("Draft", "Issued"):
        raise HTTPException(409, "Only draft or issued invoices can be updated")
    if payload.status is not None: invoice.status = payload.status
    if payload.due_date is not None: invoice.due_date = payload.due_date
    if payload.notes is not None: invoice.notes = payload.notes
    if payload.lines is not None:
        settings = settings_for_company(db, user.company_id)
        replace_lines(db, invoice, payload.lines, settings)
    invoice.updated_by = user.email
    db.commit(); db.refresh(invoice)
    return success_response(serialize_invoice(invoice, db), message="Invoice updated successfully")


@router.delete("/invoices/{invoice_id}")
def delete_invoice(invoice_id: UUID, user: Current, db: Db):
    invoice = find_invoice(db, invoice_id, user.company_id)
    if invoice.status != "Draft": raise HTTPException(409, "Only draft invoices can be deleted")
    db.delete(invoice); db.commit()
    return success_response(message="Invoice deleted successfully")
