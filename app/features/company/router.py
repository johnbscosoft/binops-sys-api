import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.responses import success_response
from app.database import get_db
from app.features.client_category.service import seed_default_client_categories
from app.features.company.models import Company
from app.features.company.schema import CompanyCreate, CompanyRead, CompanyUpdate

router = APIRouter(tags=["companies"])
DbSession = Annotated[Session, Depends(get_db)]


def find_company_or_404(db: Session, company_id: UUID) -> Company:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


def find_company_by_code_or_404(db: Session, company_code: str) -> Company:
    company = db.query(Company).filter(Company.company_code == company_code).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


def generate_company_code(db: Session) -> str:
    while True:
        company_code = f"C{secrets.randbelow(1_000_000):06d}"
        exists = db.query(Company).filter(Company.company_code == company_code).first()
        if not exists:
            return company_code


@router.post("/companies", status_code=status.HTTP_201_CREATED)
def create_company(company_data: CompanyCreate, db: DbSession) -> dict[str, object]:
    existing_company = (
        db.query(Company)
        .filter(or_(Company.name == company_data.name, Company.email == company_data.email))
        .first()
    )
    if existing_company:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Company name or email already exists",
        )

    company = Company(
        company_code=generate_company_code(db),
        **company_data.model_dump(),
    )
    db.add(company)
    db.flush()
    seed_default_client_categories(db, company.id)
    db.commit()
    db.refresh(company)
    return success_response(company)


@router.get("/companies")
def list_companies(db: DbSession) -> dict[str, object]:
    companies = db.query(Company).order_by(Company.created_at.desc()).all()
    return success_response(companies)


@router.get("/companies/{company_id}")
def get_company(company_id: UUID, db: DbSession) -> dict[str, object]:
    return success_response(find_company_or_404(db, company_id))


@router.patch("/companies/{company_id}")
def update_company(company_id: UUID, company_data: CompanyUpdate, db: DbSession) -> dict[str, object]:
    company = find_company_or_404(db, company_id)
    for field, value in company_data.model_dump(exclude_unset=True).items():
        setattr(company, field, value)

    db.commit()
    db.refresh(company)
    return success_response(company)


@router.delete("/companies/{company_id}")
def delete_company(company_id: UUID, db: DbSession) -> dict[str, object]:
    company = find_company_or_404(db, company_id)
    db.delete(company)
    db.commit()
    return success_response(message="Company deleted successfully")
