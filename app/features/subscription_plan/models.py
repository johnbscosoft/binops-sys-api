import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), index=True, nullable=False)
    duration = Column(String(80), nullable=False)
    pickup_frequency = Column(String(80), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    notes = Column(String(500), nullable=True)
    is_custom = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    company = relationship("Company", back_populates="subscription_plans")
    customers = relationship("Customer", back_populates="subscription_plan")
    properties = relationship("Property", back_populates="subscription_plan")
