from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.api.router import api_router
from app.api.responses import error_response, success_response
from app.core.config import get_settings
from app.database import Base, engine
from app.features.authentication_settings import models as authentication_settings_model
from app.features.client_category import models as client_category_model
from app.features.company import models as company_model
from app.features.contract import models as contract_model
from app.features.collection import models as collection_model
from app.features.collection_billing import models as collection_billing_model
from app.features.customer import models as customer_model
from app.features.property import models as property_model
from app.features.subscription_plan import models as subscription_plan_model
from app.features.staff import models as staff_model
from app.features.staff_designation import models as staff_designation_model
from app.features.schedule import models as schedule_model
from app.features.daily_job import models as daily_job_model
from app.features.invoice import models as invoice_model
from app.features.users import model as user_model
from app.features.vehicle import models as vehicle_model

settings = get_settings()

# Import feature models so SQLAlchemy registers their tables in Base.metadata.
_registered_models = (
    authentication_settings_model,
    client_category_model,
    company_model,
    contract_model,
    collection_model,
    collection_billing_model,
    customer_model,
    property_model,
    subscription_plan_model,
    staff_model,
    staff_designation_model,
    schedule_model,
    daily_job_model,
    invoice_model,
    user_model,
    vehicle_model,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Local-development convenience. For production, disable this and use migrations.
    if settings.auto_create_tables:
        try:
            Base.metadata.create_all(bind=engine)
        except OperationalError:
            # Keep startup output and API responses free of database internals.
            app.state.database_available = False
    yield


# Main FastAPI application instance.
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(message=str(exc.detail)),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_response(message="Validation failed", data=exc.errors()),
    )


import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)


@app.exception_handler(OperationalError)
async def database_connection_exception_handler(
    request: Request,
    exc: OperationalError,
) -> JSONResponse:
    logger.error(
        "Database operational error: method=%s path=%s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )

    return JSONResponse(
        status_code=503,
        content=error_response(
            message="Database connection failed",
        ),
    )

# Mount all feature routes under one API version prefix.
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, object]:
    # Basic app-level health check for deployment/load balancer  checks. 
    return success_response(data={"status": "ok"})
