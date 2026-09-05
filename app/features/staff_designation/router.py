from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.api.responses import success_response
from app.database import get_db
from app.features.staff_designation.models import StaffDesignation
from app.features.users.model import User
from app.features.users.router import get_current_user, require_superuser
router=APIRouter(prefix='/staff-designations', tags=['staff designations']); Db=Annotated[Session,Depends(get_db)]; Current=Annotated[User,Depends(get_current_user)]; Admin=Annotated[User,Depends(require_superuser)]
class Payload(BaseModel): name:str=Field(min_length=2,max_length=100); is_active:bool=True
def one(db,id,company):
    item=db.query(StaffDesignation).filter_by(id=id,company_id=company).first()
    if not item: raise HTTPException(404,'Designation not found')
    return item
def data(x): return {'id':x.id,'name':x.name,'is_active':x.is_active,'created_at':x.created_at}
@router.get('')
def list_items(user:Current,db:Db): return success_response([data(x) for x in db.query(StaffDesignation).filter_by(company_id=user.company_id).order_by(StaffDesignation.name).all()])
@router.post('')
def create(payload:Payload,user:Admin,db:Db):
    if db.query(StaffDesignation.id).filter(StaffDesignation.company_id==user.company_id,func.lower(StaffDesignation.name)==payload.name.strip().lower()).first(): raise HTTPException(409,'Designation already exists')
    x=StaffDesignation(company_id=user.company_id,name=payload.name.strip(),is_active=payload.is_active);db.add(x);db.commit();db.refresh(x);return success_response(data(x),message='Designation created successfully')
@router.put('/{item_id}')
def update(item_id:UUID,payload:Payload,user:Admin,db:Db):
    x=one(db,item_id,user.company_id);x.name=payload.name.strip();x.is_active=payload.is_active;db.commit();db.refresh(x);return success_response(data(x),message='Designation updated successfully')
@router.delete('/{item_id}')
def delete(item_id:UUID,user:Admin,db:Db): db.delete(one(db,item_id,user.company_id));db.commit();return success_response(message='Designation deleted successfully')
