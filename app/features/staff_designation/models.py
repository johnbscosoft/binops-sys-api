import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
class StaffDesignation(Base):
    __tablename__ = 'staff_designations'; __table_args__ = (UniqueConstraint('company_id', 'name', name='uq_staff_designations_company_name'),)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4); company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(100), nullable=False); is_active = Column(Boolean, nullable=False, default=True, server_default='true'); created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False); updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
