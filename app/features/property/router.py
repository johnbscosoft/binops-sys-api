import uuid
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.responses import success_response
from app.database import get_db
from app.features.client_category.models import ClientCategory
from app.features.customer.models import Customer
from app.features.property.models import Property, PropertyOccupancy, PropertyUnit
from app.features.property.schema import PropertyPayload, PropertyUnitInput
from app.features.subscription_plan.models import SubscriptionPlan
from app.features.users.model import User
from app.features.users.router import get_current_user

router = APIRouter(prefix="/properties", tags=["properties"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def find_property_or_404(db: Session, property_id: UUID, company_id: UUID) -> Property:
    property_record = (
        db.query(Property)
        .filter(Property.id == property_id, Property.company_id == company_id)
        .first()
    )
    if not property_record:
        raise HTTPException(status_code=404, detail="Property not found")
    return property_record


def current_occupancy(unit: PropertyUnit) -> PropertyOccupancy | None:
    return next((occupancy for occupancy in unit.occupancies if occupancy.is_current), None)


def serialize_unit(unit: PropertyUnit) -> dict:
    occupancy = current_occupancy(unit)
    customer = occupancy.customer if occupancy else None
    occupancy_status = "Occupied" if occupancy else unit.occupancy_status
    return {
        "id": unit.id,
        "property_id": unit.property_id,
        "room_number": unit.room_number,
        "is_active": unit.is_active,
        "occupancy_status": occupancy_status,
        "is_available": occupancy is None and unit.is_active and occupancy_status == "Vacant",
        "occupant_customer_id": customer.id if customer else None,
        "occupant_name": customer.name if customer else None,
    }


def serialize_property(property_record: Property) -> dict:
    units = [serialize_unit(unit) for unit in property_record.units]
    return {
        "id": property_record.id,
        "property_code": property_record.property_code,
        "name": property_record.name,
        "property_type": property_record.property_type,
        "billing_mode": property_record.billing_mode,
        "owner_customer_id": property_record.owner_customer_id,
        "owner_name": property_record.owner_name,
        "owner_phone_number": property_record.owner_phone_number,
        "owner_email": property_record.owner_email,
        "subscription_plan_id": property_record.subscription_plan_id,
        "location": property_record.location,
        "status": property_record.status,
        "unit_count": len(units),
        "occupied_unit_count": sum(unit["occupancy_status"] == "Occupied" for unit in units),
        "units": units,
        "created_at": property_record.created_at,
        "updated_at": property_record.updated_at,
    }


def validate_payload(
    db: Session,
    payload: PropertyPayload,
    company_id: UUID,
    property_id: UUID | None = None,
) -> SubscriptionPlan | None:
    duplicate = db.query(Property).filter(
        Property.company_id == company_id,
        func.lower(Property.name) == payload.name.strip().lower(),
    )
    if property_id:
        duplicate = duplicate.filter(Property.id != property_id)
    if duplicate.first():
        raise HTTPException(status_code=409, detail="A property with this name already exists")

    room_numbers: set[str] = set()
    for unit in payload.units:
        normalized = unit.room_number.strip().casefold()
        if normalized in room_numbers:
            raise HTTPException(
                status_code=422,
                detail=f"Room number '{unit.room_number}' is duplicated",
            )
        room_numbers.add(normalized)

    plan = None
    if payload.billing_mode == "OWNER":
        plan = (
            db.query(SubscriptionPlan)
            .filter(
                SubscriptionPlan.id == payload.subscription_plan_id,
                SubscriptionPlan.company_id == company_id,
                SubscriptionPlan.is_active.is_(True),
            )
            .first()
        )
        if not plan:
            raise HTTPException(status_code=404, detail="Property subscription plan not found or inactive")
    return plan


def resolve_owner_customer(
    db: Session,
    payload: PropertyPayload,
    company_id: UUID,
    plan: SubscriptionPlan | None,
) -> Customer | None:
    if payload.billing_mode != "OWNER":
        return None
    if plan is None:
        raise HTTPException(status_code=422, detail="Property subscription plan is required")

    owner = None
    if payload.owner_customer_id is not None:
        owner = (
            db.query(Customer)
            .filter(
                Customer.id == payload.owner_customer_id,
                Customer.company_id == company_id,
            )
            .first()
        )
        if not owner:
            raise HTTPException(status_code=404, detail="Linked property owner customer not found")
    if owner is None:
        individual_category = (
            db.query(ClientCategory)
            .filter(
                ClientCategory.company_id == company_id,
                func.lower(ClientCategory.name) == "individual",
            )
            .first()
        )
        if not individual_category:
            raise HTTPException(
                status_code=422,
                detail="The Individual client category is required before creating a property owner",
            )
        owner = Customer(
            company_id=company_id,
            client_category_id=individual_category.id,
            customer_type="STANDARD",
            number_of_bags=0,
            status="Active",
        )
        db.add(owner)

    # An owner-paid property is represented by a dedicated billing customer.
    # The customer's display name is the property; owner details remain on Property.
    owner.name = payload.name.strip()
    owner.phone_no = payload.owner_phone_number.strip()
    owner.email = payload.owner_email.strip().lower()
    owner.location = payload.location.strip() if payload.location else payload.name.strip()
    owner.subscription_plan_id = plan.id
    owner.status = "Active"
    db.flush()
    return owner


def sync_units(
    db: Session,
    property_record: Property,
    units: list[PropertyUnitInput],
    company_id: UUID,
) -> None:
    existing = {unit.id: unit for unit in property_record.units}
    retained: set[UUID] = set()
    for unit_data in units:
        if unit_data.id:
            unit = existing.get(unit_data.id)
            if not unit:
                raise HTTPException(status_code=404, detail=f"Room {unit_data.room_number} was not found")
            retained.add(unit.id)
        else:
            unit = PropertyUnit(property=property_record, company_id=company_id)
            db.add(unit)
        unit.room_number = unit_data.room_number.strip()
        unit.is_active = unit_data.is_active
        active_occupancy = current_occupancy(unit)
        if active_occupancy and unit_data.occupancy_status == "Vacant":
            raise HTTPException(
                status_code=409,
                detail=f"Room {unit.room_number} has an assigned customer and cannot be marked vacant",
            )
        unit.occupancy_status = "Occupied" if active_occupancy else unit_data.occupancy_status

    for unit_id, unit in existing.items():
        if unit_id in retained:
            continue
        if unit.occupancies:
            raise HTTPException(
                status_code=409,
                detail=f"Room {unit.room_number} has occupancy history and cannot be removed; deactivate it instead",
            )
        db.delete(unit)


def sync_current_customer_locations(property_record: Property) -> None:
    for unit in property_record.units:
        occupancy = current_occupancy(unit)
        if not occupancy:
            continue
        occupancy.customer.location = property_record.location
        occupancy.customer.latitude = None
        occupancy.customer.longitude = None
        occupancy.customer.place_id = None


@router.get("")
def list_properties(
    current_user: CurrentUser,
    db: DbSession,
    active_only: bool = False,
) -> dict[str, object]:
    query = db.query(Property).filter(Property.company_id == current_user.company_id)
    if active_only:
        query = query.filter(Property.status == "Active")
    properties = query.order_by(Property.name.asc()).all()
    return success_response([serialize_property(item) for item in properties])


@router.get("/{property_id}/units")
def list_property_units(
    property_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    available_only: bool = False,
    include_customer_id: int | None = None,
) -> dict[str, object]:
    property_record = find_property_or_404(db, property_id, current_user.company_id)
    units = [serialize_unit(unit) for unit in property_record.units if unit.is_active]
    if available_only:
        units = [
            unit for unit in units
            if unit["is_available"] or unit["occupant_customer_id"] == include_customer_id
        ]
    return success_response(units)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_property(
    payload: PropertyPayload,
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, object]:
    plan = validate_payload(db, payload, current_user.company_id)
    owner = resolve_owner_customer(db, payload, current_user.company_id, plan)
    property_record = Property(
        company_id=current_user.company_id,
        property_code=f"PROP-{uuid.uuid4().hex[:8].upper()}",
        name=payload.name.strip(),
        property_type=payload.property_type,
        billing_mode=payload.billing_mode,
        owner_customer_id=owner.id if owner else None,
        owner_name=payload.owner_name.strip() if owner else None,
        owner_phone_number=payload.owner_phone_number.strip() if owner else None,
        owner_email=payload.owner_email.strip().lower() if owner else None,
        subscription_plan_id=plan.id if plan else None,
        location=payload.location.strip(),
        status=payload.status,
    )
    db.add(property_record)
    db.flush()
    sync_units(db, property_record, payload.units, current_user.company_id)
    db.commit()
    db.refresh(property_record)
    return success_response(serialize_property(property_record), message="Property created successfully")


@router.put("/{property_id}")
def update_property(
    property_id: UUID,
    payload: PropertyPayload,
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, object]:
    property_record = find_property_or_404(db, property_id, current_user.company_id)
    plan = validate_payload(db, payload, current_user.company_id, property_id)
    owner = resolve_owner_customer(db, payload, current_user.company_id, plan)
    property_record.name = payload.name.strip()
    property_record.property_type = payload.property_type
    property_record.billing_mode = payload.billing_mode
    property_record.owner_customer_id = owner.id if owner else None
    property_record.owner_name = payload.owner_name.strip() if owner else None
    property_record.owner_phone_number = payload.owner_phone_number.strip() if owner else None
    property_record.owner_email = payload.owner_email.strip().lower() if owner else None
    property_record.subscription_plan_id = plan.id if plan else None
    property_record.location = payload.location.strip()
    property_record.status = payload.status
    sync_units(db, property_record, payload.units, current_user.company_id)
    sync_current_customer_locations(property_record)
    db.commit()
    db.refresh(property_record)
    return success_response(serialize_property(property_record), message="Property updated successfully")


@router.delete("/{property_id}")
def delete_property(
    property_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, object]:
    property_record = find_property_or_404(db, property_id, current_user.company_id)
    occupancy = (
        db.query(PropertyOccupancy.id)
        .join(PropertyUnit, PropertyUnit.id == PropertyOccupancy.property_unit_id)
        .filter(PropertyUnit.property_id == property_record.id)
        .first()
    )
    if occupancy:
        raise HTTPException(
            status_code=409,
            detail="This property has occupancy history and cannot be deleted; deactivate it instead",
        )
    db.delete(property_record)
    db.commit()
    return success_response(message="Property deleted successfully")
