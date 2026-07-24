from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.responses import success_response
from app.database import get_db
from app.features.subscription_plan.models import SubscriptionPlan
from app.features.subscription_plan.schema import SubscriptionPlanCreate, SubscriptionPlanUpdate
from app.features.users.model import User
from app.features.users.router import get_current_user

router = APIRouter(prefix="/subscription-plans", tags=["subscription plans"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def find_plan_or_404(db: Session, plan_id: UUID, company_id: UUID) -> SubscriptionPlan:
    plan = (
        db.query(SubscriptionPlan)
        .filter(
            SubscriptionPlan.id == plan_id,
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


@router.post("", status_code=status.HTTP_201_CREATED)
def create_subscription_plan(
    plan_data: SubscriptionPlanCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, object]:
    plan = SubscriptionPlan(company_id=current_user.company_id, **plan_data.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return success_response(plan, message="Subscription plan created successfully")


@router.get("")
def list_subscription_plans(
    current_user: CurrentUser,
    db: DbSession,
    active_only: bool = False,
) -> dict[str, object]:
    query = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.company_id == current_user.company_id
    )
    if active_only:
        query = query.filter(SubscriptionPlan.is_active.is_(True))
    plans = query.order_by(SubscriptionPlan.created_at.desc()).all()
    return success_response(plans)


@router.get("/{plan_id}")
def get_subscription_plan(
    plan_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, object]:
    return success_response(find_plan_or_404(db, plan_id, current_user.company_id))


@router.patch("/{plan_id}")
def update_subscription_plan(
    plan_id: UUID,
    plan_data: SubscriptionPlanUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, object]:
    plan = find_plan_or_404(db, plan_id, current_user.company_id)
    updates = plan_data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(plan, field, value)
    db.commit()
    db.refresh(plan)
    return success_response(plan, message="Subscription plan updated successfully")


@router.delete("/{plan_id}")
def delete_subscription_plan(
    plan_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, object]:
    plan = find_plan_or_404(db, plan_id, current_user.company_id)
    db.delete(plan)
    db.commit()
    return success_response(message="Subscription plan deleted successfully")
