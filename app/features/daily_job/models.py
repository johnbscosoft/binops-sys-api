import uuid
from sqlalchemy import Column,Date,DateTime,Float,ForeignKey,Integer,String,Text,UniqueConstraint,func
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
class DailyJob(Base):
 __tablename__='daily_jobs';__table_args__=(UniqueConstraint('company_id','job_code',name='uq_daily_jobs_company_code'),UniqueConstraint('company_id','schedule_id','job_date',name='uq_daily_jobs_schedule_date'))
 id=Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4);company_id=Column(UUID(as_uuid=True),ForeignKey('companies.id',ondelete='CASCADE'),nullable=False);job_code=Column(String(60),nullable=False);schedule_id=Column(UUID(as_uuid=True),ForeignKey('collection_schedules.id',ondelete='SET NULL'));area_id=Column(UUID(as_uuid=True),ForeignKey('collection_areas.id'),nullable=False);route_id=Column(UUID(as_uuid=True),ForeignKey('collection_routes.id'),nullable=False);job_date=Column(Date,nullable=False);vehicle_id=Column(UUID(as_uuid=True),ForeignKey('vehicles.id',ondelete='SET NULL'));driver_id=Column(UUID(as_uuid=True),ForeignKey('staff.id',ondelete='SET NULL'));status=Column(String(30),default='Draft');created_at=Column(DateTime(timezone=True),server_default=func.now())
class TodaysPickup(Base):
 __tablename__='todays_pickups';__table_args__=(UniqueConstraint('daily_job_id','customer_id',name='uq_todays_pickups_job_customer'),)
 id=Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4);daily_job_id=Column(UUID(as_uuid=True),ForeignKey('daily_jobs.id',ondelete='CASCADE'),nullable=False);customer_id=Column(Integer,ForeignKey('customer.id'),nullable=False);stop_order=Column(Integer,nullable=False);status=Column(String(30),default='Pending');notes=Column(Text);bags_issued=Column(Integer,default=0);before_photo=Column(Text);after_photo=Column(Text);completed_at=Column(DateTime(timezone=True));collector_latitude=Column(Float);collector_longitude=Column(Float)
