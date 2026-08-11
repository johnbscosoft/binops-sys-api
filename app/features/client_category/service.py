from uuid import UUID

from sqlalchemy.orm import Session

from app.features.client_category.models import ClientCategory

DEFAULT_CLIENT_CATEGORIES = (
    "Individual",
    "Apartment",
    "Shopping Mall",
    "School",
    "University",
    "Rentals",
)


def seed_default_client_categories(db: Session, company_id: UUID) -> bool:
    existing_names = {
        name.lower()
        for (name,) in db.query(ClientCategory.name)
        .filter(ClientCategory.company_id == company_id)
        .all()
    }
    missing = [
        ClientCategory(company_id=company_id, name=name)
        for name in DEFAULT_CLIENT_CATEGORIES
        if name.lower() not in existing_names
    ]
    if not missing:
        return False
    db.add_all(missing)
    db.flush()
    return True
