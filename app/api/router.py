from fastapi import APIRouter

from app.features.authentication_settings.router import router as authentication_settings_router
from app.features.client_category.router import router as client_category_router
from app.features.company.router import router as company_router
from app.features.contract.router import router as contract_router
from app.features.customer.router import router as customer_router
from app.features.property.router import router as property_router
from app.features.subscription_plan.router import router as subscription_plan_router
from app.features.users.router import router as users_router

# Central API router. Add each feature router here once, then app/main.py
# mounts everything under the configured API prefix, e.g. /api/v1.
api_router = APIRouter()
api_router.include_router(authentication_settings_router)
api_router.include_router(client_category_router)
api_router.include_router(company_router)
api_router.include_router(contract_router)
api_router.include_router(customer_router)
api_router.include_router(property_router)
api_router.include_router(subscription_plan_router)
api_router.include_router(users_router)
