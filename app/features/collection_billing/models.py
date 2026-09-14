import uuid

from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class CollectionBillingRecord(Base):
    __tablename__ = "collection_billing_records"
    __table_args__ = (
        UniqueConstraint("collection_id", name="uq_collection_billing_records_collection_id"),
        CheckConstraint("number_of_bags >= 0", name="ck_collection_billing_records_bags_nonnegative"),
        CheckConstraint("unit_rate >= 0", name="ck_collection_billing_records_unit_rate_nonnegative"),
        CheckConstraint("calculated_amount >= 0", name="ck_collection_billing_records_amount_nonnegative"),
        CheckConstraint("billing_status IN ('Unbilled', 'Draft Invoice', 'Invoiced', 'Waived')", name="ck_collection_billing_records_status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False, index=True)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("todays_pickups.id"), nullable=False)
    daily_job_id = Column(UUID(as_uuid=True), ForeignKey("daily_jobs.id"), nullable=False, index=True)
    subscription_plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False, index=True)
    pickup_date = Column(Date, nullable=False, index=True)
    billing_month = Column(String(7), nullable=False, index=True)
    billing_period_start = Column(Date, nullable=False)
    billing_period_end = Column(Date, nullable=False)
    number_of_bags = Column(Integer, nullable=False, default=0, server_default="0")
    unit_rate = Column(Numeric(14, 2), nullable=False)
    calculated_amount = Column(Numeric(14, 2), nullable=False)
    invoice_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    billing_status = Column(String(30), nullable=False, default="Unbilled", server_default="Unbilled", index=True)
    currency = Column(String(3), nullable=False, default="UGX", server_default="UGX")
    description = Column(Text, nullable=False)
    created_by = Column(String(255), nullable=True)
    updated_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
