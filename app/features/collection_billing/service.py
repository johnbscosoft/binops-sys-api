from calendar import monthrange

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.features.collection_billing.models import CollectionBillingRecord
from app.features.customer.models import Customer
from app.features.daily_job.models import DailyJob, TodaysPickup
from app.features.users.model import User


COMPLETED_PICKUP_STATUSES = {"Collected", "Partially Collected"}
MISSED_PICKUP_STATUSES = {"Missed", "Not Collected"}


def create_collection_billing_record(db: Session, pickup: TodaysPickup, user: User) -> CollectionBillingRecord:
    """Create one immutable-rate billing record per completed pickup."""
    existing = db.query(CollectionBillingRecord).filter_by(collection_id=pickup.id).first()
    if existing:
        return existing

    job = db.query(DailyJob).filter_by(id=pickup.daily_job_id, company_id=user.company_id).first()
    customer = db.query(Customer).filter_by(id=pickup.customer_id, company_id=user.company_id).first()
    if not job or not customer:
        raise HTTPException(status_code=422, detail="Pickup customer or daily job could not be billed")
    if not customer.subscription_plan or not customer.subscription_plan.is_active:
        raise HTTPException(status_code=422, detail="Assign an active subscription plan before completing this pickup")

    pickup_date = job.job_date
    period_start = pickup_date.replace(day=1)
    period_end = pickup_date.replace(day=monthrange(pickup_date.year, pickup_date.month)[1])
    plan = customer.subscription_plan
    record = CollectionBillingRecord(
        company_id=user.company_id,
        customer_id=customer.id,
        collection_id=pickup.id,
        daily_job_id=job.id,
        subscription_plan_id=plan.id,
        pickup_date=pickup_date,
        billing_month=pickup_date.strftime("%Y-%m"),
        billing_period_start=period_start,
        billing_period_end=period_end,
        number_of_bags=max(0, pickup.bags_issued or 0),
        unit_rate=plan.amount,
        calculated_amount=plan.amount,
        billing_status="Unbilled",
        currency="UGX",
        description=f"Waste collection on {pickup_date:%d %b %Y} — {plan.pickup_frequency}",
        created_by=user.email,
        updated_by=user.email,
    )
    db.add(record)
    return record


def waive_unbilled_collection_record(db: Session, pickup: TodaysPickup, user: User) -> None:
    """Keep an audit trail if a previously completed pickup is marked missed."""
    record = db.query(CollectionBillingRecord).filter_by(collection_id=pickup.id, billing_status="Unbilled").first()
    if record:
        record.billing_status = "Waived"
        record.updated_by = user.email
