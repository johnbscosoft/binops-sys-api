

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.responses import success_response
from app.database import get_db
from app.features.customer.models import Customer
from app.features.customer.schema import CreateCustomer
from app.features.subscription_plan.models import SubscriptionPlan
from app.features.users.model import User
from app.features.users.router import get_current_user

router = APIRouter(tags=["Customer"])

DbSession = Annotated[Session, Depends(get_db)]


def find_company_plan_or_404(
    db: Session,
    subscription_plan_id,
    company_id,
) -> SubscriptionPlan:
    plan = (
        db.query(SubscriptionPlan)
        .filter(
            SubscriptionPlan.id == subscription_plan_id,
            SubscriptionPlan.company_id == company_id,
        )
        .first()
    )
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found",
        )
    return plan



@router.post("/customers")
def create_customer(
    customer: CreateCustomer,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession
):
    plan = find_company_plan_or_404(db, customer.subscription_plan_id, current_user.company_id)
    db_customer = Customer(
        company_id=current_user.company_id,
        name=customer.name,
        phone_no=customer.phone_no,
        email=customer.email,
        location=customer.location,
        latitude=customer.latitude,
        longitude=customer.longitude,
        place_id=customer.place_id,
        flat_no=customer.flat_no,
        house_no=customer.house_no,
        subscription_plan_id=plan.id,
        status=customer.status,
        added_by=customer.added_by,
        updated_by=customer.updated_by,
    )

    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)

    return success_response(db_customer)

@router.get("/customers")
def get_customers(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
):
    customers = db.query(Customer).filter(Customer.company_id == current_user.company_id).all()
    return success_response(customers)

@router.get("/customers/{customer_id}")
def get_customer(
    customer_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
):
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.company_id == current_user.company_id)
        .first()
    )
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return success_response(customer)

@router.delete("/customers/{customer_id}")
def delete_customer(
    customer_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
):
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.company_id == current_user.company_id)
        .first()
    )
    if customer:
        db.delete(customer)
        db.commit()
        return success_response(message="Customer deleted successfully")
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    
@router.put("/customers/{customer_id}")
def update_customer(
    customer_id: int,
    customer: CreateCustomer,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
):
    plan = find_company_plan_or_404(db, customer.subscription_plan_id, current_user.company_id)
    db_customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.company_id == current_user.company_id)
        .first()
    )
    if db_customer:
        db_customer.name = customer.name
        db_customer.phone_no = customer.phone_no
        db_customer.email = customer.email
        db_customer.location = customer.location
        db_customer.latitude = customer.latitude
        db_customer.longitude = customer.longitude
        db_customer.place_id = customer.place_id
        db_customer.flat_no = customer.flat_no
        db_customer.house_no = customer.house_no
        db_customer.subscription_plan_id = plan.id
        db_customer.status = customer.status
        db_customer.updated_by = customer.updated_by

        db.commit()
        db.refresh(db_customer)
        return success_response(db_customer)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    
