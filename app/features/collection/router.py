from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.responses import success_response
from app.database import get_db
from app.features.collection.models import CollectionArea, CollectionRoute, ContractingOrganisation
from app.features.collection.schema import CollectionAreaPayload, CollectionRoutePayload, ContractingOrganisationPayload
from app.features.users.model import User
from app.features.users.router import get_current_user, require_superuser
from app.features.vehicle.models import Vehicle

router = APIRouter(prefix="/collection", tags=["waste collection"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Superuser = Annotated[User, Depends(require_superuser)]


def area_or_404(db: Session, area_id: UUID, company_id: UUID) -> CollectionArea:
    area = db.query(CollectionArea).filter(CollectionArea.id == area_id, CollectionArea.company_id == company_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Collection area not found")
    return area


def route_or_404(db: Session, route_id: UUID, company_id: UUID) -> CollectionRoute:
    route = db.query(CollectionRoute).filter(CollectionRoute.id == route_id, CollectionRoute.company_id == company_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Collection route not found")
    return route


def serialize_area(area: CollectionArea) -> dict:
    return {
        "id": area.id, "company_id": area.company_id, "area_code": area.area_code,
        "name": area.name, "description": area.description, "location": area.location,
        "latitude": area.latitude, "longitude": area.longitude, "place_id": area.place_id, "status": area.status,
        "service_model": area.service_model, "contracting_organisation_id": area.contracting_organisation_id,
        "created_at": area.created_at, "updated_at": area.updated_at,
    }

def serialize_organisation(item: ContractingOrganisation) -> dict:
    return {"id": item.id, "name": item.name, "commission_type": item.commission_type, "commission_rate": item.commission_rate, "contract_start_date": item.contract_start_date, "contract_end_date": item.contract_end_date}


def serialize_route(route: CollectionRoute, db: Session) -> dict:
    vehicle = db.query(Vehicle).filter(Vehicle.id == route.vehicle_id, Vehicle.company_id == route.company_id).first() if route.vehicle_id else None
    return {
        "id": route.id, "company_id": route.company_id, "area_id": route.area_id,
        "area_code": route.area_code, "route_code": route.route_code, "area_name": route.area.name if route.area else None,
        "name": route.name, "vehicle_id": route.vehicle_id, "vehicle_plate": vehicle.plate_number if vehicle else None, "status": route.status,
        "created_at": route.created_at, "updated_at": route.updated_at,
    }


def validate_route_area(db: Session, payload: CollectionRoutePayload, company_id: UUID) -> CollectionArea:
    area = area_or_404(db, payload.area_id, company_id)
    if area.area_code.casefold() != payload.area_code.casefold():
        raise HTTPException(status_code=422, detail="The selected area code does not match the selected area")
    return area


def validate_route_vehicle(db: Session, vehicle_id: UUID | None, company_id: UUID) -> None:
    if vehicle_id and not db.query(Vehicle.id).filter(Vehicle.id == vehicle_id, Vehicle.company_id == company_id).first():
        raise HTTPException(status_code=422, detail="Select a vehicle belonging to your company")


@router.get("/areas")
def list_areas(current_user: CurrentUser, db: DbSession) -> dict[str, object]:
    areas = db.query(CollectionArea).filter(CollectionArea.company_id == current_user.company_id).order_by(CollectionArea.name).all()
    return success_response([serialize_area(area) for area in areas])


@router.post("/areas", status_code=status.HTTP_201_CREATED)
def create_area(payload: CollectionAreaPayload, current_user: Superuser, db: DbSession) -> dict[str, object]:
    if payload.service_model == "SUBCONTRACT" and not payload.contracting_organisation_id: raise HTTPException(status_code=422, detail="Select a contracting organisation")
    area_code = payload.area_code or f"{''.join(c for c in payload.name.upper() if c.isalnum())[:3].ljust(3, 'X')}-{db.query(CollectionArea).filter(CollectionArea.company_id == current_user.company_id).count()+1:03d}"
    duplicate = db.query(CollectionArea).filter(CollectionArea.company_id == current_user.company_id, func.lower(CollectionArea.area_code) == area_code.lower()).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="An area with this code already exists")
    area = CollectionArea(company_id=current_user.company_id, **{**payload.model_dump(), "area_code": area_code})
    db.add(area); db.commit(); db.refresh(area)
    return success_response(serialize_area(area), message="Collection area created successfully")


@router.put("/areas/{area_id}")
def update_area(area_id: UUID, payload: CollectionAreaPayload, current_user: Superuser, db: DbSession) -> dict[str, object]:
    if payload.service_model == "SUBCONTRACT" and not payload.contracting_organisation_id: raise HTTPException(status_code=422, detail="Select a contracting organisation")
    area = area_or_404(db, area_id, current_user.company_id)
    duplicate = db.query(CollectionArea).filter(CollectionArea.company_id == current_user.company_id, func.lower(CollectionArea.area_code) == payload.area_code.lower(), CollectionArea.id != area.id).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="An area with this code already exists")
    for field, value in payload.model_dump().items(): setattr(area, field, value)
    db.commit(); db.refresh(area)
    return success_response(serialize_area(area), message="Collection area updated successfully")

@router.get("/contracting-organisations")
def list_contracting_organisations(current_user: CurrentUser, db: DbSession):
    items = db.query(ContractingOrganisation).filter(ContractingOrganisation.company_id == current_user.company_id).order_by(ContractingOrganisation.name).all()
    return success_response([serialize_organisation(item) for item in items])

@router.post("/contracting-organisations", status_code=status.HTTP_201_CREATED)
def create_contracting_organisation(payload: ContractingOrganisationPayload, current_user: Superuser, db: DbSession):
    item = ContractingOrganisation(company_id=current_user.company_id, **payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return success_response(serialize_organisation(item), message="Contracting organisation created successfully")


@router.delete("/areas/{area_id}")
def delete_area(area_id: UUID, current_user: Superuser, db: DbSession) -> dict[str, object]:
    area = area_or_404(db, area_id, current_user.company_id)
    if db.query(CollectionRoute.id).filter(CollectionRoute.area_id == area.id).first():
        raise HTTPException(status_code=409, detail="This area has routes and cannot be deleted")
    db.delete(area); db.commit()
    return success_response(message="Collection area deleted successfully")


@router.get("/routes")
def list_routes(current_user: CurrentUser, db: DbSession) -> dict[str, object]:
    routes = db.query(CollectionRoute).filter(CollectionRoute.company_id == current_user.company_id).order_by(CollectionRoute.name).all()
    return success_response([serialize_route(route, db) for route in routes])


@router.post("/routes", status_code=status.HTTP_201_CREATED)
def create_route(payload: CollectionRoutePayload, current_user: Superuser, db: DbSession) -> dict[str, object]:
    validate_route_area(db, payload, current_user.company_id)
    validate_route_vehicle(db, payload.vehicle_id, current_user.company_id)
    duplicate = db.query(CollectionRoute).filter(CollectionRoute.company_id == current_user.company_id, func.lower(CollectionRoute.name) == payload.name.lower()).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="A route with this name already exists")
    route_code = payload.route_code or f"{payload.area_code.split('-')[0]}-R{db.query(CollectionRoute).filter(CollectionRoute.company_id == current_user.company_id, CollectionRoute.area_code == payload.area_code).count()+1:02d}"
    route = CollectionRoute(company_id=current_user.company_id, **{**payload.model_dump(), "route_code": route_code})
    db.add(route); db.commit(); db.refresh(route)
    return success_response(serialize_route(route, db), message="Collection route created successfully")


@router.put("/routes/{route_id}")
def update_route(route_id: UUID, payload: CollectionRoutePayload, current_user: Superuser, db: DbSession) -> dict[str, object]:
    route = route_or_404(db, route_id, current_user.company_id)
    validate_route_area(db, payload, current_user.company_id)
    validate_route_vehicle(db, payload.vehicle_id, current_user.company_id)
    duplicate = db.query(CollectionRoute).filter(CollectionRoute.company_id == current_user.company_id, func.lower(CollectionRoute.name) == payload.name.lower(), CollectionRoute.id != route.id).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="A route with this name already exists")
    for field, value in payload.model_dump().items(): setattr(route, field, value)
    db.commit(); db.refresh(route)
    return success_response(serialize_route(route, db), message="Collection route updated successfully")


@router.delete("/routes/{route_id}")
def delete_route(route_id: UUID, current_user: Superuser, db: DbSession) -> dict[str, object]:
    route = route_or_404(db, route_id, current_user.company_id)
    db.delete(route); db.commit()
    return success_response(message="Collection route deleted successfully")
