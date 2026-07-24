from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


from app.database import Base

class Customer(Base):
    __tablename__ = "customer"

    id = Column(Integer, primary_key=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), index=True, nullable=False)
    name = Column(String)
    phone_no = Column(String)
    email = Column(String)
    location = Column(String)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    place_id = Column(String, nullable=True)
    flat_no = Column(String, nullable=True)
    house_no = Column(String, nullable=True)
    subscription_plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscription_plans.id"),
        index=True,
        nullable=True,
    )
    status = Column(String, default="Active", nullable=False)
    date_entered = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    date_updated = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    added_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)

    company = relationship("Company", back_populates="customers")
    subscription_plan = relationship("SubscriptionPlan", back_populates="customers")
