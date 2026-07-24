import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class CustomerContract(Base):
    __tablename__ = "customer_contracts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_code = Column(String(40), unique=True, index=True, nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customer.id"), index=True, nullable=False)
    subscription_plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscription_plans.id"),
        index=True,
        nullable=False,
    )
    customer_code = Column(String(40), nullable=False)
    customer_name = Column(String, nullable=False)
    plan_duration = Column(String(80), nullable=False)
    pickup_frequency = Column(String(80), nullable=False)
    agreed_amount = Column(Numeric(14, 2), nullable=False)
    start_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    company = relationship("Company")
    customer = relationship("Customer")
    subscription_plan = relationship("SubscriptionPlan")
    creator = relationship("User")
