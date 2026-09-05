import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


from app.database import Base

class Customer(Base):
    __tablename__ = "customer"
    __table_args__ = (
        CheckConstraint("number_of_bags >= 0", name="ck_customer_number_of_bags_nonnegative"),
        CheckConstraint(
            "service_arrangement IS NULL OR service_arrangement IN ('LANDLORD', 'DIRECT_TENANT')",
            name="ck_customer_service_arrangement",
        ),
        CheckConstraint(
            "room_pricing_mode IS NULL OR room_pricing_mode IN ('SHARED', 'PER_ROOM')",
            name="ck_customer_room_pricing_mode",
        ),
        CheckConstraint(
            "customer_type IN ('STANDARD', 'PROPERTY', 'OCCUPANT')",
            name="ck_customer_customer_type",
        ),
    )

    id = Column(Integer, primary_key=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), index=True, nullable=False)
    collection_route_id = Column(UUID(as_uuid=True), ForeignKey("collection_routes.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String)
    phone_no = Column(String, nullable=True)
    email = Column(String, nullable=True)
    location = Column(String)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    place_id = Column(String, nullable=True)
    flat_no = Column(String, nullable=True)
    house_no = Column(String, nullable=True)
    number_of_bags = Column(Integer, default=0, server_default="0", nullable=False)
    notes = Column(String(1000), nullable=True)
    customer_type = Column(String(20), default="STANDARD", server_default="STANDARD", nullable=False)
    agreed_price = Column(Numeric(14, 2), nullable=True)
    service_arrangement = Column(String(30), nullable=True)
    room_pricing_mode = Column(String(20), nullable=True)
    caretaker_name = Column(String(160), nullable=True)
    caretaker_phone = Column(String(40), nullable=True)
    client_category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("client_categories.id"),
        index=True,
        nullable=False,
    )
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
    client_category = relationship("ClientCategory", back_populates="customers")
    subscription_plan = relationship("SubscriptionPlan", back_populates="customers")
    rooms = relationship(
        "CustomerRoom",
        back_populates="customer",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="CustomerRoom.room_number",
    )
    room_occupancies = relationship(
        "RoomOccupancy",
        back_populates="occupant_customer",
        foreign_keys="RoomOccupancy.occupant_customer_id",
    )
    property_occupancies = relationship(
        "PropertyOccupancy",
        back_populates="customer",
        foreign_keys="PropertyOccupancy.customer_id",
    )


class CustomerRoom(Base):
    __tablename__ = "customer_rooms"
    __table_args__ = (
        UniqueConstraint("customer_id", "room_number", name="uq_customer_rooms_customer_room"),
        CheckConstraint("number_of_bags >= 0", name="ck_customer_rooms_bags_nonnegative"),
        CheckConstraint(
            "occupancy_status IN ('Occupied', 'Vacant')",
            name="ck_customer_rooms_occupancy_status",
        ),
        CheckConstraint(
            "account_status IN ('Active', 'Inactive')",
            name="ck_customer_rooms_account_status",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(
        Integer,
        ForeignKey("customer.id", ondelete="CASCADE"),
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
    occupancy_status = Column(String(20), default="Vacant", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    customer = relationship("Customer", back_populates="rooms")
    occupancies = relationship(
        "RoomOccupancy",
        back_populates="room",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="RoomOccupancy.start_date",
    )


class RoomOccupancy(Base):
    __tablename__ = "room_occupancies"
    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_room_occupancies_date_order",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_rooms.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    occupant_customer_id = Column(
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

    room = relationship("CustomerRoom", back_populates="occupancies")
    occupant_customer = relationship(
        "Customer",
        back_populates="room_occupancies",
        foreign_keys=[occupant_customer_id],
    )
