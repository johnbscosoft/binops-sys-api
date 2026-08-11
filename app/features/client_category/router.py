from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.responses import success_response
from app.database import get_db
from app.features.client_category.models import ClientCategory
from app.features.client_category.schema import ClientCategoryCreate, ClientCategoryUpdate
from app.features.client_category.service import seed_default_client_categories
from app.features.customer.models import Customer
from app.features.users.model import User
from app.features.users.router import get_current_user, require_superuser

router = APIRouter(prefix="/client-categories", tags=["client categories"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Superuser = Annotated[User, Depends(require_superuser)]

def find_category_or_404(
    db: Session,
    category_id: UUID,
    company_id: UUID,
) -> ClientCategory:
    category = (
        db.query(ClientCategory)
        .filter(
            ClientCategory.id == category_id,
            ClientCategory.company_id == company_id,
        )
        .first()
    )
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client category not found",
        )
    return category


def ensure_unique_name(
    db: Session,
    company_id: UUID,
    name: str,
    exclude_id: UUID | None = None,
) -> None:
    query = db.query(ClientCategory).filter(
        ClientCategory.company_id == company_id,
        func.lower(ClientCategory.name) == name.lower(),
    )
    if exclude_id:
        query = query.filter(ClientCategory.id != exclude_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A client category with this name already exists",
        )


@router.get("")
def list_client_categories(
    current_user: CurrentUser,
    db: DbSession,
    active_only: bool = False,
) -> dict[str, object]:
    if seed_default_client_categories(db, current_user.company_id):
        db.commit()
    query = db.query(ClientCategory).filter(
        ClientCategory.company_id == current_user.company_id
    )
    if active_only:
        query = query.filter(ClientCategory.is_active.is_(True))
    categories = query.order_by(ClientCategory.name.asc()).all()
    return success_response(categories)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_client_category(
    category_data: ClientCategoryCreate,
    current_user: Superuser,
    db: DbSession,
) -> dict[str, object]:
    ensure_unique_name(db, current_user.company_id, category_data.name)
    category = ClientCategory(
        company_id=current_user.company_id,
        **category_data.model_dump(),
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return success_response(category, message="Client category created successfully")


@router.patch("/{category_id}")
def update_client_category(
    category_id: UUID,
    category_data: ClientCategoryUpdate,
    current_user: Superuser,
    db: DbSession,
) -> dict[str, object]:
    category = find_category_or_404(db, category_id, current_user.company_id)
    updates = category_data.model_dump(exclude_unset=True)
    if "name" in updates:
        ensure_unique_name(db, current_user.company_id, updates["name"], category.id)
    for field, value in updates.items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return success_response(category, message="Client category updated successfully")


@router.delete("/{category_id}")
def delete_client_category(
    category_id: UUID,
    current_user: Superuser,
    db: DbSession,
) -> dict[str, object]:
    category = find_category_or_404(db, category_id, current_user.company_id)
    assigned_clients = db.query(Customer.id).filter(
        Customer.company_id == current_user.company_id,
        Customer.client_category_id == category.id,
    ).first()
    if assigned_clients:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This category is assigned to one or more clients and cannot be deleted",
        )
    db.delete(category)
    db.commit()
    return success_response(message="Client category deleted successfully")
