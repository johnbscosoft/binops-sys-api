import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_properties_company_name"),
        CheckConstraint(
            "property_type IN ('APARTMENT', 'RENTAL')",
            name="ck_properties_type",
        ),
        CheckConstraint(
            "billing_mode IN ('OWNER', 'TENANT')",
            name="ck_properties_billing_mode",
        ),
        CheckConstraint(
            "status IN ('Active', 'Inactive')",
            name="ck_properties_status",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    property_code = Column(String(30), unique=True, index=True, nullable=False)
    name = Column(String(160), nullable=False)
    property_type = Column(String(20), nullable=False)
    billing_mode = Column(String(20), nullable=False)
    owner_customer_id = Column(Integer, ForeignKey("customer.id"), nullable=True, index=True)
    owner_name = Column(String(160), nullable=True)
    owner_phone_number = Column(String(40), nullable=True)
    owner_email = Column(String(255), nullable=True)
    subscription_plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscription_plans.id"),
        nullable=True,
        index=True,
    )
    location = Column(String(500), nullable=True)
    status = Column(String(20), default="Active", server_default="Active", nullable=False)
    legacy_customer_id = Column(Integer, nullable=True, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    company = relationship("Company", back_populates="properties")
    owner_customer = relationship("Customer", foreign_keys=[owner_customer_id])
    subscription_plan = relationship("SubscriptionPlan", back_populates="properties")
    units = relationship(
        "PropertyUnit",
        back_populates="property",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PropertyUnit.room_number",
    )


class PropertyUnit(Base):
    __tablename__ = "property_units"
    __table_args__ = (
        UniqueConstraint("property_id", "room_number", name="uq_property_units_room"),
        CheckConstraint(
            "occupancy_status IN ('Occupied', 'Vacant')",
            name="ck_property_units_occupancy_status",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    room_number = Column(String(80), nullable=False)
    is_active = Column(Boolean, default=True, server_default="true", nullable=False)
    occupancy_status = Column(String(20), default="Vacant", server_default="Vacant", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    property = relationship("Property", back_populates="units")
    occupancies = relationship(
        "PropertyOccupancy",
        back_populates="unit",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PropertyOccupancy.start_date",
    )


class PropertyOccupancy(Base):
    __tablename__ = "property_occupancies"
    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_property_occupancies_date_order",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_unit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("property_units.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    customer_id = Column(
        Integer,
        ForeignKey("customer.id"),
        index=True,
        nullable=False,
    )
    start_date = Column(Date, server_default=func.current_date(), nullable=False)
    end_date = Column(Date, nullable=True)
    is_current = Column(Boolean, default=True, server_default="true", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    unit = relationship("PropertyUnit", back_populates="occupancies")
    customer = relationship(
        "Customer",
        back_populates="property_occupancies",
        foreign_keys=[customer_id],
    )
