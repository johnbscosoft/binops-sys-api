import calendar
import re
import uuid
from datetime import date, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.responses import success_response
from app.database import get_db
from app.features.company.models import Company
from app.features.contract.models import CustomerContract
from app.features.contract.pdf import generate_contract_pdf
from app.features.contract.schema import CustomerContractCreate
from app.features.customer.models import Customer
from app.features.subscription_plan.models import SubscriptionPlan
from app.features.users.model import User
from app.features.users.router import get_current_user

router = APIRouter(prefix="/contracts", tags=["customer contracts"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _add_months(value: date, months: int) -> date:
    target_month = value.month - 1 + months
    year = value.year + target_month // 12
    month = target_month % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def calculate_expiry_date(start_date: date, duration: str) -> date:
    match = re.search(r"(\d+)\s*(day|week|month|year)s?", duration, re.IGNORECASE)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This plan duration cannot be calculated. Enter an expiry date.",
        )
    count = int(match.group(1))
    unit = match.group(2).lower()
    if unit == "day":
        return start_date + timedelta(days=count)
    if unit == "week":
        return start_date + timedelta(weeks=count)
    if unit == "month":
        return _add_months(start_date, count)
    return _add_months(start_date, count * 12)


def _find_contract(db: Session, contract_id: UUID, company_id: UUID) -> CustomerContract:
    contract = (
        db.query(CustomerContract)
        .filter(
            CustomerContract.id == contract_id,
            CustomerContract.company_id == company_id,
        )
        .first()
    )
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    return contract


@router.post("", status_code=status.HTTP_201_CREATED)
def create_contract(
    contract_data: CustomerContractCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, object]:
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == contract_data.customer_id,
            Customer.company_id == current_user.company_id,
        )
        .first()
    )
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    if not customer.subscription_plan_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Select a subscription plan for this customer before generating a contract",
        )
    plan = (
        db.query(SubscriptionPlan)
        .filter(
            SubscriptionPlan.id == customer.subscription_plan_id,
            SubscriptionPlan.company_id == current_user.company_id,
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription plan not found")
    expiry_date = contract_data.expiry_date or calculate_expiry_date(
        contract_data.start_date, plan.duration
    )
    if expiry_date <= contract_data.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Expiry date must be after the start date",
        )
    contract = CustomerContract(
        contract_code=f"CON-{date.today().year}-{uuid.uuid4().hex[:8].upper()}",
        company_id=current_user.company_id,
        customer_id=customer.id,
        subscription_plan_id=plan.id,
        customer_code=f"CUST-{customer.id:04d}",
        customer_name=customer.name,
        plan_duration=plan.duration,
        pickup_frequency=plan.pickup_frequency,
        agreed_amount=plan.amount,
        start_date=contract_data.start_date,
        expiry_date=expiry_date,
        created_by=current_user.id,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return success_response(contract, message="Contract generated successfully")


@router.get("")
def list_contracts(current_user: CurrentUser, db: DbSession) -> dict[str, object]:
    contracts = (
        db.query(CustomerContract)
        .filter(CustomerContract.company_id == current_user.company_id)
        .order_by(CustomerContract.created_at.desc())
        .all()
    )
    return success_response(contracts)


@router.get("/{contract_id}")
def get_contract(contract_id: UUID, current_user: CurrentUser, db: DbSession) -> dict[str, object]:
    return success_response(_find_contract(db, contract_id, current_user.company_id))


@router.get("/{contract_id}/pdf")
def view_contract_pdf(contract_id: UUID, current_user: CurrentUser, db: DbSession) -> Response:
    contract = _find_contract(db, contract_id, current_user.company_id)
    customer = (
        db.query(Customer)
        .filter(Customer.id == contract.customer_id, Customer.company_id == current_user.company_id)
        .first()
    )
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    if not customer or not company:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Contract customer or company details are unavailable",
        )
    pdf = generate_contract_pdf(contract, customer, company)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{contract.contract_code}.pdf"',
            "Cache-Control": "no-store",
        },
    )


@router.delete("/{contract_id}")
def delete_contract(contract_id: UUID, current_user: CurrentUser, db: DbSession) -> dict[str, object]:
    contract = _find_contract(db, contract_id, current_user.company_id)
    db.delete(contract)
    db.commit()
    return success_response(message="Contract deleted successfully")
