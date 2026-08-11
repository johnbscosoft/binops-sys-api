from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.responses import success_response
from app.database import get_db
from app.features.client_category.models import ClientCategory
from app.features.customer.models import Customer
from app.features.customer.schema import CreateCustomer
from app.features.property.models import Property, PropertyOccupancy, PropertyUnit
from app.features.subscription_plan.models import SubscriptionPlan
from app.features.users.model import User
from app.features.users.router import get_current_user

router = APIRouter(tags=["Customer"])
DbSession = Annotated[Session, Depends(get_db)]
PROPERTY_CATEGORIES = {"apartment": "APARTMENT", "rentals": "RENTAL"}


def find_company_category_or_404(
    db: Session,
    client_category_id,
    company_id,
    active_only: bool = True,
) -> ClientCategory:
    query = db.query(ClientCategory).filter(
        ClientCategory.id == client_category_id,
        ClientCategory.company_id == company_id,
    )
    if active_only:
        query = query.filter(ClientCategory.is_active.is_(True))
    category = query.first()
    if not category:
        raise HTTPException(status_code=404, detail="Client category not found or inactive")
    return category


def find_company_plan_or_404(db: Session, plan_id, company_id) -> SubscriptionPlan:
    plan = (
        db.query(SubscriptionPlan)
        .filter(
            SubscriptionPlan.id == plan_id,
            SubscriptionPlan.company_id == company_id,
            SubscriptionPlan.is_active.is_(True),
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found or inactive")
    return plan


def active_property_occupancy(customer: Customer) -> PropertyOccupancy | None:
    return next(
        (occupancy for occupancy in customer.property_occupancies if occupancy.is_current),
        None,
    )


def validate_customer_payload(
    db: Session,
    payload: CreateCustomer,
    category: ClientCategory,
    company_id,
    customer_id: int | None = None,
) -> tuple[SubscriptionPlan | None, Property | None, PropertyUnit | None]:
    expected_property_type = PROPERTY_CATEGORIES.get(category.name.strip().casefold())
    property_record = None
    unit = None

    if expected_property_type:
        if not payload.property_id or not payload.property_unit_id:
            raise HTTPException(
                status_code=422,
                detail="Property and room number are required for Apartment and Rentals customers",
            )
        property_record = (
            db.query(Property)
            .filter(
                Property.id == payload.property_id,
                Property.company_id == company_id,
                Property.status == "Active",
            )
            .first()
        )
        if not property_record:
            raise HTTPException(status_code=404, detail="Property not found or inactive")
        if not property_record.location or not property_record.location.strip():
            raise HTTPException(
                status_code=422,
                detail="The selected property must have a location before customers can be assigned",
            )
        if property_record.property_type != expected_property_type:
            raise HTTPException(
                status_code=422,
                detail="The selected property type does not match the client category",
            )
        unit = (
            db.query(PropertyUnit)
            .filter(
                PropertyUnit.id == payload.property_unit_id,
                PropertyUnit.property_id == property_record.id,
                PropertyUnit.company_id == company_id,
                PropertyUnit.is_active.is_(True),
            )
            .first()
        )
        if not unit:
            raise HTTPException(status_code=404, detail="Room not found or inactive")
        occupied = next((item for item in unit.occupancies if item.is_current), None)
        if occupied and occupied.customer_id != customer_id:
            raise HTTPException(status_code=409, detail="The selected room is already occupied")
    elif payload.property_id or payload.property_unit_id:
        raise HTTPException(
            status_code=422,
            detail="Property assignment is only available for Apartment and Rentals customers",
        )

    plan = None
    plan_required = property_record is None or property_record.billing_mode == "TENANT"
    if plan_required:
        if not payload.subscription_plan_id:
            raise HTTPException(status_code=422, detail="Subscription plan is required")
        plan = find_company_plan_or_404(db, payload.subscription_plan_id, company_id)
    return plan, property_record, unit


def close_occupancy(occupancy: PropertyOccupancy) -> None:
    occupancy.is_current = False
    occupancy.end_date = date.today()
    occupancy.unit.occupancy_status = "Vacant"


def sync_property_occupancy(
    db: Session,
    customer: Customer,
    property_record: Property | None,
    unit: PropertyUnit | None,
    start_date: date | None,
) -> None:
    active = active_property_occupancy(customer)
    if customer.status == "Inactive" or not property_record or not unit:
        if active:
            close_occupancy(active)
        return
    if active and active.property_unit_id == unit.id:
        unit.occupancy_status = "Occupied"
        if start_date:
            active.start_date = start_date
        return
    if active:
        close_occupancy(active)
    unit.occupancy_status = "Occupied"
    db.add(
        PropertyOccupancy(
            property_unit_id=unit.id,
            customer_id=customer.id,
            start_date=start_date or date.today(),
        )
    )


def serialize_customer(customer: Customer) -> dict:
    occupancy = active_property_occupancy(customer)
    unit = occupancy.unit if occupancy else None
    property_record = unit.property if unit else None
    return {
        "id": customer.id,
        "company_id": customer.company_id,
        "name": customer.name,
        "phone_no": customer.phone_no,
        "email": customer.email,
        "location": customer.location,
        "latitude": customer.latitude,
        "longitude": customer.longitude,
        "place_id": customer.place_id,
        "flat_no": customer.flat_no,
        "house_no": customer.house_no,
        "number_of_bags": customer.number_of_bags,
        "notes": customer.notes,
        "customer_type": "STANDARD",
        "agreed_price": customer.agreed_price,
        "client_category_id": customer.client_category_id,
        "subscription_plan_id": customer.subscription_plan_id,
        "property_id": property_record.id if property_record else None,
        "property_name": property_record.name if property_record else None,
        "property_type": property_record.property_type if property_record else None,
        "property_billing_mode": property_record.billing_mode if property_record else None,
        "property_unit_id": unit.id if unit else None,
        "room_number": unit.room_number if unit else None,
        "occupancy_start_date": occupancy.start_date if occupancy else None,
        "status": customer.status,
        "date_entered": customer.date_entered,
        "date_updated": customer.date_updated,
        "added_by": customer.added_by,
        "updated_by": customer.updated_by,
        # Deprecated response keys retained while older UI builds are phased out.
        "service_arrangement": None,
        "room_pricing_mode": None,
        "caretaker_name": None,
        "caretaker_phone": None,
        "property_customer_id": None,
        "room_id": unit.id if unit else None,
        "rooms": [],
    }


def apply_customer_values(
    customer: Customer,
    payload: CreateCustomer,
    category: ClientCategory,
    plan: SubscriptionPlan | None,
    property_record: Property | None,
) -> None:
    customer.name = payload.name.strip()
    customer.phone_no = payload.phone_no.strip()
    customer.email = payload.email.strip()
    if property_record:
        customer.location = property_record.location.strip()
        customer.latitude = None
        customer.longitude = None
        customer.place_id = None
    else:
        customer.location = payload.location.strip()
        customer.latitude = payload.latitude
        customer.longitude = payload.longitude
        customer.place_id = payload.place_id
    customer.flat_no = payload.flat_no
    customer.house_no = payload.house_no
    customer.number_of_bags = payload.number_of_bags
    customer.notes = payload.notes.strip() if payload.notes else None
    customer.customer_type = "STANDARD"
    customer.agreed_price = payload.agreed_price if not property_record or property_record.billing_mode == "TENANT" else None
    customer.client_category_id = category.id
    customer.subscription_plan_id = plan.id if plan else None
    customer.service_arrangement = None
    customer.room_pricing_mode = None
    customer.caretaker_name = None
    customer.caretaker_phone = None
    customer.status = payload.status
    customer.added_by = payload.added_by or customer.added_by
    customer.updated_by = payload.updated_by


@router.post("/customers", status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CreateCustomer,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
):
    category = find_company_category_or_404(db, payload.client_category_id, current_user.company_id)
    plan, property_record, unit = validate_customer_payload(
        db, payload, category, current_user.company_id
    )
    customer = Customer(company_id=current_user.company_id)
    apply_customer_values(customer, payload, category, plan, property_record)
    db.add(customer)
    db.flush()
    sync_property_occupancy(db, customer, property_record, unit, payload.occupancy_start_date)
    db.commit()
    db.refresh(customer)
    return success_response(serialize_customer(customer), message="Customer created successfully")


@router.get("/customers")
def get_customers(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
):
    customers = (
        db.query(Customer)
        .filter(Customer.company_id == current_user.company_id)
        .order_by(Customer.date_entered.desc())
        .all()
    )
    return success_response([serialize_customer(customer) for customer in customers])


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
        raise HTTPException(status_code=404, detail="Customer not found")
    return success_response(serialize_customer(customer))


@router.put("/customers/{customer_id}")
def update_customer(
    customer_id: int,
    payload: CreateCustomer,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
):
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.company_id == current_user.company_id)
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    category = find_company_category_or_404(
        db,
        payload.client_category_id,
        current_user.company_id,
        active_only=customer.client_category_id != payload.client_category_id,
    )
    plan, property_record, unit = validate_customer_payload(
        db, payload, category, current_user.company_id, customer.id
    )
    apply_customer_values(customer, payload, category, plan, property_record)
    sync_property_occupancy(db, customer, property_record, unit, payload.occupancy_start_date)
    db.commit()
    db.refresh(customer)
    return success_response(serialize_customer(customer), message="Customer updated successfully")


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
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if customer.property_occupancies:
        raise HTTPException(
            status_code=409,
            detail="This customer has property occupancy history and cannot be deleted; deactivate the customer instead",
        )
    property_owned = db.query(Property.id).filter(Property.owner_customer_id == customer.id).first()
    if property_owned:
        raise HTTPException(
            status_code=409,
            detail="This customer owns a property and cannot be deleted until the property is reassigned",
        )
    db.delete(customer)
    db.commit()
    return success_response(message="Customer deleted successfully")
