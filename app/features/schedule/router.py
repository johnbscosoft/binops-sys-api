from typing import Annotated
from uuid import UUID
from datetime import date
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.responses import success_response
from app.features.collection.models import CollectionArea,CollectionRoute
from app.features.schedule.models import CollectionSchedule
from app.features.users.model import User
from app.features.users.router import get_current_user,require_superuser
router=APIRouter(prefix='/schedules',tags=['schedules']); Db=Annotated[Session,Depends(get_db)]; Current=Annotated[User,Depends(get_current_user)]; Admin=Annotated[User,Depends(require_superuser)]
class Payload(BaseModel): area_id:UUID; route_id:UUID; collection_days:list[str]=Field(min_length=1); start_date:date; end_date:date|None=None; vehicle_id:UUID|None=None; driver_id:UUID|None=None; status:str='Active'
def serialize(x,db):
 a=db.query(CollectionArea).get(x.area_id);r=db.query(CollectionRoute).get(x.route_id);return {'id':x.id,'schedule_code':x.schedule_code,'area_id':x.area_id,'area_name':a.name if a else None,'route_id':x.route_id,'route_name':r.name if r else None,'collection_days':x.collection_days.split(','),'start_date':x.start_date,'end_date':x.end_date,'vehicle_id':x.vehicle_id,'driver_id':x.driver_id,'status':x.status,'created_at':x.created_at}
@router.get('')
def list_items(user:Current,db:Db): return success_response([serialize(x,db) for x in db.query(CollectionSchedule).filter_by(company_id=user.company_id).order_by(CollectionSchedule.start_date.desc()).all()])
@router.post('')
def create(p:Payload,user:Admin,db:Db):
 route=db.query(CollectionRoute).filter_by(id=p.route_id,company_id=user.company_id,area_id=p.area_id).first()
 if not route: raise HTTPException(422,'Select a route belonging to the selected area')
 code=f'SCH-{db.query(CollectionSchedule).filter_by(company_id=user.company_id).count()+1:04d}';x=CollectionSchedule(company_id=user.company_id,schedule_code=code,area_id=p.area_id,route_id=p.route_id,collection_days=','.join(p.collection_days),start_date=p.start_date,end_date=p.end_date,vehicle_id=p.vehicle_id,driver_id=p.driver_id,status=p.status);db.add(x);db.commit();db.refresh(x);return success_response(serialize(x,db),message='Schedule created successfully')
@router.delete('/{item_id}')
def delete(item_id:UUID,user:Admin,db:Db):
 x=db.query(CollectionSchedule).filter_by(id=item_id,company_id=user.company_id).first()
 if not x: raise HTTPException(404,'Schedule not found')
 db.delete(x);db.commit();return success_response(message='Schedule deleted successfully')
