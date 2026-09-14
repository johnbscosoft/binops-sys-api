import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"
    __table_args__ = (UniqueConstraint("company_id", "plate_number", name="uq_vehicles_company_plate"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    plate_number = Column(String(40), nullable=False)
    model = Column(String(160), nullable=False)
    chassis_number = Column(String(100), nullable=True)
    vehicle_type = Column(String(100), nullable=True)
    purchase_date = Column(Date, nullable=True)
    third_party_insurance_expiry = Column(Date, nullable=True)
    truck_photo_name = Column(String(255), nullable=True)
    truck_photo_data = Column(Text, nullable=True)
    logbook_name = Column(String(255), nullable=True)
    logbook_data = Column(Text, nullable=True)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="Active", server_default="Active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    driver = relationship("Staff", foreign_keys=[driver_id])
