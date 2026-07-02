from fastapi import APIRouter

from app.features.customer.router import router as customer_router
from app.features.users.router import router as users_router

# Central API router. Add each feature router here once, then app/main.py
# mounts everything under the configured API prefix, e.g. /api/v1.
api_router = APIRouter()
api_router.include_router(customer_router)
api_router.include_router(users_router)
