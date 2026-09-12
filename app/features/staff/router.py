from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.responses import success_response
from app.database import get_db
from app.features.staff.models import Staff
from app.features.staff.schema import StaffPayload
from app.features.users.model import User
from app.features.users.router import get_current_user, require_superuser

router = APIRouter(prefix="/staff", tags=["staff"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Superuser = Annotated[User, Depends(require_superuser)]


def staff_or_404(db: Session, staff_id: UUID, company_id: UUID) -> Staff:
    item = db.query(Staff).filter(Staff.id == staff_id, Staff.company_id == company_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Staff member not found")
    return item


def serialize(item: Staff) -> dict:
    return {key: getattr(item, key) for key in (
        "id", "company_id", "first_name", "last_name", "employment_date", "designation", "phone_number", "residence", "permit_number",
        "permit_expiry_date", "date_of_birth", "gender", "attachment_name", "attachment_data", "status", "created_at", "updated_at",
    )}


@router.get("")
def list_staff(current_user: CurrentUser, db: DbSession):
    items = db.query(Staff).filter(Staff.company_id == current_user.company_id).order_by(Staff.first_name, Staff.last_name).all()
    return success_response([serialize(item) for item in items])


@router.get("/drivers")
def list_drivers(current_user: CurrentUser, db: DbSession):
    items = db.query(Staff).filter(Staff.company_id == current_user.company_id, func.lower(Staff.designation) == "driver", Staff.status == "Active").order_by(Staff.first_name, Staff.last_name).all()
    return success_response([serialize(item) for item in items])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_staff(payload: StaffPayload, current_user: Superuser, db: DbSession):
    try:
        item = Staff(company_id=current_user.company_id, **payload.model_dump())
        db.add(item)
        db.commit()
        db.refresh(item)
        return success_response(serialize(item), message="Staff member created successfully")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Staff member could not be saved. Please try again.")


@router.put("/{staff_id}")
def update_staff(staff_id: UUID, payload: StaffPayload, current_user: Superuser, db: DbSession):
    item = staff_or_404(db, staff_id, current_user.company_id)
    for field, value in payload.model_dump().items(): setattr(item, field, value)
    db.commit(); db.refresh(item)
    return success_response(serialize(item), message="Staff member updated successfully")


@router.delete("/{staff_id}")
def delete_staff(staff_id: UUID, current_user: Superuser, db: DbSession):
    item = staff_or_404(db, staff_id, current_user.company_id)
    db.delete(item); db.commit()
    return success_response(message="Staff member deleted successfully")
