import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Staff(Base):
    __tablename__ = "staff"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    employment_date = Column(Date, nullable=True)
    designation = Column(String(20), nullable=False)
    phone_number = Column(String(40), nullable=True)
    residence = Column(String(500), nullable=True)
    permit_number = Column(String(100), nullable=True)
    permit_expiry_date = Column(Date, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    attachment_name = Column(String(255), nullable=True)
    attachment_data = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="Active", server_default="Active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
