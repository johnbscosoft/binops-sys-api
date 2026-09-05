from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api.responses import success_response
from app.database import get_db
from app.features.customer.models import Customer
from app.features.collection.models import CollectionArea,CollectionRoute
from app.features.daily_job.models import DailyJob,TodaysPickup
from app.features.schedule.models import CollectionSchedule
from app.features.users.model import User
from app.features.users.router import get_current_user,require_superuser
router=APIRouter(prefix='/daily-jobs',tags=['daily jobs']);Db=Annotated[Session,Depends(get_db)];Current=Annotated[User,Depends(get_current_user)];Admin=Annotated[User,Depends(require_superuser)]
class Payload(BaseModel): schedule_id:UUID;job_date:date
class PickupUpdate(BaseModel): bags_issued:int=0; status:str; notes:str|None=None; before_photo:str|None=None; after_photo:str|None=None; collector_latitude:float; collector_longitude:float
def serial(x,db):
 return {'id':x.id,'job_code':x.job_code,'schedule_id':x.schedule_id,'job_date':x.job_date,'area_id':x.area_id,'route_id':x.route_id,'vehicle_id':x.vehicle_id,'driver_id':x.driver_id,'status':x.status,'todays_pickups_count':db.query(TodaysPickup).filter_by(daily_job_id=x.id).count(),'created_at':x.created_at}
@router.get('')
def list_jobs(user:Current,db:Db):return success_response([serial(x,db) for x in db.query(DailyJob).filter_by(company_id=user.company_id).order_by(DailyJob.job_date.desc()).all()])
@router.post('')
def generate(p:Payload,user:Admin,db:Db):
 s=db.query(CollectionSchedule).filter_by(id=p.schedule_id,company_id=user.company_id).first()
 if not s:raise HTTPException(422,'Select a valid schedule')
 if db.query(DailyJob).filter_by(company_id=user.company_id,schedule_id=s.id,job_date=p.job_date).first():raise HTTPException(409,'A job already exists for this schedule and date')
 x=DailyJob(company_id=user.company_id,job_code=f'JOB-{p.job_date:%Y%m%d}-{db.query(DailyJob).filter_by(company_id=user.company_id).count()+1:03d}',schedule_id=s.id,area_id=s.area_id,route_id=s.route_id,job_date=p.job_date,vehicle_id=s.vehicle_id,driver_id=s.driver_id);db.add(x);db.flush()
 for index,c in enumerate(db.query(Customer).filter_by(company_id=user.company_id,collection_route_id=s.route_id,status='Active').order_by(Customer.id).all(),1):db.add(TodaysPickup(daily_job_id=x.id,customer_id=c.id,stop_order=index))
 db.commit();db.refresh(x);return success_response(serial(x,db),message='Daily job generated successfully')

@router.get('/{job_id}/todays-pickups')
def list_todays_pickups(job_id:UUID,user:Current,db:Db):
 job=db.query(DailyJob).filter_by(id=job_id,company_id=user.company_id).first()
 if not job: raise HTTPException(404,'Daily job not found')
 pickups=db.query(TodaysPickup,Customer,DailyJob,CollectionArea,CollectionRoute).join(Customer,Customer.id==TodaysPickup.customer_id).join(DailyJob,DailyJob.id==TodaysPickup.daily_job_id).join(CollectionArea,CollectionArea.id==DailyJob.area_id).join(CollectionRoute,CollectionRoute.id==DailyJob.route_id).filter(TodaysPickup.daily_job_id==job.id).order_by(TodaysPickup.stop_order).all()
 return success_response([{'id':pickup.id,'pickup_order':pickup.stop_order,'status':pickup.status,'notes':pickup.notes,'bags_issued':pickup.bags_issued,'configured_bags':customer.number_of_bags,'subscription_plan':f'{customer.subscription_plan.duration} — {customer.subscription_plan.pickup_frequency}' if customer.subscription_plan else None,'customer_id':customer.id,'customer_name':customer.name,'customer_code':f'CUST-{customer.id:04d}','phone_number':customer.phone_no,'location':customer.location,'latitude':customer.latitude,'longitude':customer.longitude,'route_id':job.route_id,'area_code':area.area_code,'area_name':area.name,'route_code':route.route_code,'route_name':route.name} for pickup,customer,_,area,route in pickups])

@router.get('/pickups/today')
def list_all_todays_pickups(user:Current,db:Db,job_date:date|None=None,route_id:UUID|None=None):
 target=job_date or datetime.now(ZoneInfo("Africa/Kampala")).date()
 query=db.query(TodaysPickup,Customer,DailyJob,CollectionArea,CollectionRoute).join(DailyJob,DailyJob.id==TodaysPickup.daily_job_id).join(Customer,Customer.id==TodaysPickup.customer_id).join(CollectionArea,CollectionArea.id==DailyJob.area_id).join(CollectionRoute,CollectionRoute.id==DailyJob.route_id).filter(DailyJob.company_id==user.company_id,DailyJob.job_date==target)
 if route_id: query=query.filter(DailyJob.route_id==route_id)
 rows=query.order_by(DailyJob.job_code,TodaysPickup.stop_order).all()
 return success_response([{'id':p.id,'job_code':j.job_code,'pickup_order':p.stop_order,'status':p.status,'bags_issued':p.bags_issued,'configured_bags':c.number_of_bags,'subscription_plan':f'{c.subscription_plan.duration} — {c.subscription_plan.pickup_frequency}' if c.subscription_plan else None,'customer_name':c.name,'customer_code':f'CUST-{c.id:04d}','phone_number':c.phone_no,'location':c.location,'latitude':c.latitude,'longitude':c.longitude,'route_id':j.route_id,'area_code':area.area_code,'area_name':area.name,'route_code':route.route_code,'route_name':route.name} for p,c,j,area,route in rows])

@router.put('/todays-pickups/{pickup_id}')
def update_pickup(pickup_id:UUID,payload:PickupUpdate,user:Current,db:Db):
 pickup=db.query(TodaysPickup).join(DailyJob,DailyJob.id==TodaysPickup.daily_job_id).filter(TodaysPickup.id==pickup_id,DailyJob.company_id==user.company_id).first()
 if not pickup: raise HTTPException(404,'Today’s pickup not found')
 pickup.bags_issued=max(0,payload.bags_issued);pickup.status=payload.status;pickup.notes=payload.notes;pickup.before_photo=payload.before_photo;pickup.after_photo=payload.after_photo;pickup.collector_latitude=payload.collector_latitude;pickup.collector_longitude=payload.collector_longitude;pickup.completed_at=datetime.now(timezone.utc) if payload.status in ('Collected','Partially Collected') else None
 db.commit();return success_response(message='Pickup updated successfully')
