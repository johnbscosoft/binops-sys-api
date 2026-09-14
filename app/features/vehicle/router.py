from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.responses import success_response
from app.database import get_db
from app.features.staff.models import Staff
from app.features.users.model import User
from app.features.users.router import get_current_user, require_superuser
from app.features.vehicle.models import Vehicle
from app.features.vehicle.schema import VehiclePayload

router = APIRouter(prefix="/vehicles", tags=["vehicles"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Superuser = Annotated[User, Depends(require_superuser)]


def vehicle_or_404(db: Session, vehicle_id: UUID, company_id: UUID) -> Vehicle:
    item = db.query(Vehicle).options(joinedload(Vehicle.driver)).filter(Vehicle.id == vehicle_id, Vehicle.company_id == company_id).first()
    if not item: raise HTTPException(status_code=404, detail="Vehicle not found")
    return item


def validate_driver(db: Session, driver_id: UUID | None, company_id: UUID) -> None:
    if driver_id and not db.query(Staff.id).filter(Staff.id == driver_id, Staff.company_id == company_id, func.lower(Staff.designation) == "driver", Staff.status == "Active").first():
        raise HTTPException(status_code=422, detail="Select an active staff member designated as a driver")


def serialize(item: Vehicle) -> dict:
    driver_name = None if not item.driver else f"{item.driver.first_name} {item.driver.last_name}"
    return {"id": item.id, "company_id": item.company_id, "plate_number": item.plate_number, "model": item.model, "chassis_number": item.chassis_number, "vehicle_type": item.vehicle_type, "purchase_date": item.purchase_date, "third_party_insurance_expiry": item.third_party_insurance_expiry, "truck_photo_name": item.truck_photo_name, "truck_photo_data": item.truck_photo_data, "logbook_name": item.logbook_name, "logbook_data": item.logbook_data, "driver_id": item.driver_id, "driver_name": driver_name, "status": item.status, "created_at": item.created_at, "updated_at": item.updated_at}


@router.get("")
def list_vehicles(current_user: CurrentUser, db: DbSession):
    items = db.query(Vehicle).options(joinedload(Vehicle.driver)).filter(Vehicle.company_id == current_user.company_id).order_by(Vehicle.plate_number).all()
    return success_response([serialize(item) for item in items])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_vehicle(payload: VehiclePayload, current_user: Superuser, db: DbSession):
    validate_driver(db, payload.driver_id, current_user.company_id)
    if db.query(Vehicle.id).filter(Vehicle.company_id == current_user.company_id, func.lower(Vehicle.plate_number) == payload.plate_number.lower()).first():
        raise HTTPException(status_code=409, detail="A vehicle with this plate number already exists")
    item = Vehicle(company_id=current_user.company_id, **{**payload.model_dump(), "plate_number": payload.plate_number.upper().strip(), "model": payload.model.strip()})
    db.add(item); db.commit(); db.refresh(item)
    return success_response(serialize(item), message="Vehicle created successfully")


@router.put("/{vehicle_id}")
def update_vehicle(vehicle_id: UUID, payload: VehiclePayload, current_user: Superuser, db: DbSession):
    item = vehicle_or_404(db, vehicle_id, current_user.company_id)
    validate_driver(db, payload.driver_id, current_user.company_id)
    if db.query(Vehicle.id).filter(Vehicle.company_id == current_user.company_id, func.lower(Vehicle.plate_number) == payload.plate_number.lower(), Vehicle.id != item.id).first():
        raise HTTPException(status_code=409, detail="A vehicle with this plate number already exists")
    for field, value in payload.model_dump().items(): setattr(item, field, value)
    item.plate_number, item.model = payload.plate_number.upper().strip(), payload.model.strip()
    db.commit(); db.refresh(item)
    return success_response(serialize(item), message="Vehicle updated successfully")


@router.delete("/{vehicle_id}")
def delete_vehicle(vehicle_id: UUID, current_user: Superuser, db: DbSession):
    item = vehicle_or_404(db, vehicle_id, current_user.company_id)
    db.delete(item); db.commit()
    return success_response(message="Vehicle deleted successfully")
