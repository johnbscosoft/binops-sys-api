import uuid

from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String, index=True, nullable=False)
    logo = Column(String, nullable=True)
    contact_person = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    users = relationship("User", back_populates="company")
    roles = relationship("Role", back_populates="company")
    customers = relationship("Customer", back_populates="company")
    subscription_plans = relationship(
        "SubscriptionPlan",
        back_populates="company",
        cascade="all, delete-orphan",
    )
    authentication_settings = relationship(
        "AuthenticationSettings",
        back_populates="company",
        cascade="all, delete-orphan",
        uselist=False,
    )
