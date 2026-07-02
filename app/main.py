from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.database import Base, engine
from app.features.customer import models as customer_model
from app.features.users import model as user_model

settings = get_settings()

# Import feature models so SQLAlchemy registers their tables in Base.metadata.
_registered_models = (customer_model, user_model)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Local-development convenience. For production, disable this and use migrations.
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    yield


# Main FastAPI application instance.
app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Mount all feature routes under one API version prefix.
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    # Basic app-level health check for deployment/load balancer checks.
    return {"status": "ok"}
