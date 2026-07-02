

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.features.customer.models import Customer
from app.features.customer.schema import CreateCustomer

router = APIRouter(tags=["Customer"])

DbSession = Annotated[Session, Depends(get_db)]



@router.post("/customers")
def create_customer(
    customer: CreateCustomer,
    db: DbSession
):
    db_customer = Customer(
        name=customer.name,
        phone_no=customer.phone_no,
        email=customer.email,
        location=customer.location,
        subscription_type=customer.subscription_type,
        contract_amount=customer.contract_amount,
        added_by=customer.added_by,
        updated_by=customer.updated_by,
    )

    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)

    return db_customer

@router.get("/customers")
def get_customers(db: DbSession):
    return db.query(Customer).all()

@router.get("/customers/{customer_id}")
def get_customer(customer_id: int, db: DbSession):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer

@router.delete("/customers/{customer_id}")
def delete_customer(customer_id: int, db: DbSession):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if customer:
        db.delete(customer)
        db.commit()
        return {"message": "Customer deleted successfully"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    
@router.put("/customers/{customer_id}")
def update_customer(customer_id: int, customer: CreateCustomer, db: DbSession):
    db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if db_customer:
        db_customer.name = customer.name
        db_customer.phone_no = customer.phone_no
        db_customer.email = customer.email
        db_customer.location = customer.location
        db_customer.subscription_type = customer.subscription_type
        db_customer.contract_amount = customer.contract_amount
        db_customer.updated_by = customer.updated_by

        db.commit()
        db.refresh(db_customer)
        return db_customer
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    
