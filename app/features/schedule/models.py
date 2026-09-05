import uuid
from sqlalchemy import Column, Date, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
class CollectionSchedule(Base):
 __tablename__='collection_schedules'; __table_args__=(UniqueConstraint('company_id','schedule_code',name='uq_collection_schedules_company_code'),)
 id=Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4); company_id=Column(UUID(as_uuid=True),ForeignKey('companies.id',ondelete='CASCADE'),nullable=False,index=True); schedule_code=Column(String(50),nullable=False); area_id=Column(UUID(as_uuid=True),ForeignKey('collection_areas.id'),nullable=False); route_id=Column(UUID(as_uuid=True),ForeignKey('collection_routes.id'),nullable=False); collection_days=Column(String(200),nullable=False); start_date=Column(Date,nullable=False); end_date=Column(Date); vehicle_id=Column(UUID(as_uuid=True),ForeignKey('vehicles.id',ondelete='SET NULL')); driver_id=Column(UUID(as_uuid=True),ForeignKey('staff.id',ondelete='SET NULL')); status=Column(String(20),nullable=False,default='Active'); created_at=Column(DateTime(timezone=True),server_default=func.now()); updated_at=Column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())
