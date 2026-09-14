from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.responses import success_response
from app.database import get_db
from app.features.collection_billing.models import CollectionBillingRecord
from app.features.users.model import User
from app.features.users.router import get_current_user

router = APIRouter(prefix="/collection-billing", tags=["collection billing"])
Db = Annotated[Session, Depends(get_db)]
Current = Annotated[User, Depends(get_current_user)]


def serialize(record: CollectionBillingRecord) -> dict:
    return {
        "id": record.id,
        "company_id": record.company_id,
        "customer_id": record.customer_id,
        "collection_id": record.collection_id,
        "daily_job_id": record.daily_job_id,
        "subscription_plan_id": record.subscription_plan_id,
        "pickup_date": record.pickup_date,
        "billing_month": record.billing_month,
        "billing_period_start": record.billing_period_start,
        "billing_period_end": record.billing_period_end,
        "number_of_bags": record.number_of_bags,
        "unit_rate": record.unit_rate,
        "calculated_amount": record.calculated_amount,
        "invoice_id": record.invoice_id,
        "billing_status": record.billing_status,
        "currency": record.currency,
        "description": record.description,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


@router.get("")
def list_collection_billing_records(
    user: Current,
    db: Db,
    billing_month: str | None = None,
    billing_status: str | None = None,
    customer_id: int | None = None,
    daily_job_id: UUID | None = None,
):
    query = db.query(CollectionBillingRecord).filter_by(company_id=user.company_id)
    if billing_month:
        query = query.filter(CollectionBillingRecord.billing_month == billing_month)
    if billing_status:
        query = query.filter(CollectionBillingRecord.billing_status == billing_status)
    if customer_id:
        query = query.filter(CollectionBillingRecord.customer_id == customer_id)
    if daily_job_id:
        query = query.filter(CollectionBillingRecord.daily_job_id == daily_job_id)
    return success_response([serialize(record) for record in query.order_by(CollectionBillingRecord.pickup_date.desc(), CollectionBillingRecord.created_at.desc()).all()])
