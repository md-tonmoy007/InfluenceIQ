from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from backend.api.middleware.cors import setup_cors
from backend.api.middleware.error_handlers import register_error_handlers
from backend.api.middleware.request_logging import setup_logging_middleware
from backend.api.routers import auth, campaigns, demo, health, influencers, lists, onboarding, websocket, workspace
from backend.api.routers import settings as settings_router
from backend.api.schemas.errors import ErrorEnvelope
from backend.core.config import settings
from backend.core.lifecycle import StartupValidationError, validate_settings

# Initialize structlog configuration
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
        if settings.APP_ENV == "prod"
        else structlog.processors.KeyValueRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Validate required settings before serving traffic.

    Failures here raise at process boot — they are intentionally
    loud because a misconfigured deployment is worse than a crashed one.
    """
    try:
        summary = validate_settings()
    except StartupValidationError as exc:
        logger.error("startup_validation_failed", error=str(exc))
        raise
    logger.info("startup_validation_passed", **summary)
    yield
    logger.info("api_shutdown")


# Create FastAPI instance
app = FastAPI(
    title="InfluenceIQ",
    description=(
        "Trust-Aware Influencer Discovery Platform Backend.\n\n"
        "All write endpoints accept an ``Idempotency-Key`` header so "
        "clients can safely retry without doubling side effects. All "
        "non-2xx responses follow the :class:`ErrorEnvelope` shape."
    ),
    version="0.1.0",
    lifespan=lifespan,
    responses={
        422: {"model": ErrorEnvelope, "description": "Validation error"},
        404: {"model": ErrorEnvelope, "description": "Resource not found"},
        409: {"model": ErrorEnvelope, "description": "Idempotency conflict"},
        500: {"model": ErrorEnvelope, "description": "Internal server error"},
    },
)

# Setup CORS and Custom Logging middleware
setup_cors(app)
setup_logging_middleware(app)

# Register global error handlers so every response uses ErrorEnvelope.
register_error_handlers(app)

# Register endpoints routers
app.include_router(auth.router)
app.include_router(health.router)
app.include_router(onboarding.router)
app.include_router(settings_router.router)
app.include_router(campaigns.router)
app.include_router(influencers.router)
app.include_router(lists.router)
app.include_router(workspace.router)
app.include_router(demo.router)
app.include_router(websocket.router)


@app.get("/")
def root() -> dict[str, str]:
    """Service description endpoint."""
    return {
        "service": "InfluenceIQ Backend API",
        "version": app.version,
        "environment": settings.APP_ENV,
        "docs_url": "/docs",
    }


def _custom_openapi() -> dict:
    """Tag every endpoint with a stable ``x-influenceiq-tag`` for tooling.

    FastAPI's default tag inference uses the router's ``tags`` argument;
    we keep that and add the schema once here so Swagger UI renders
    the :class:`ErrorEnvelope` correctly in the response example list.
    """
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=[
            {"name": "auth", "description": "Signup, login, token refresh, current-user lookup."},
            {"name": "onboarding", "description": "Create/retrieve the current user's brand profile."},
            {"name": "settings", "description": "Notifications, integrations, API keys, subscription."},
            {"name": "campaigns", "description": "Create, list, retrieve, and inspect campaigns."},
            {"name": "influencers", "description": "Influencer profile, score history, brand-safety flags."},
            {"name": "lists", "description": "User-curated saved lists of influencers."},
            {"name": "workspace", "description": "Dashboard summary, activity feed, and counts."},
            {"name": "websocket", "description": "Real-time pipeline event stream with replay."},
            {"name": "demo", "description": "Idempotent demo seed path used by `make seed`."},
            {"name": "health", "description": "Liveness, readiness, queue depth, and worker gauges."},
            {"name": "system", "description": "Service metadata and root endpoint."},
        ],
        servers=[
            {"url": "http://localhost:8002", "description": "Local docker compose"},
            {"url": "http://localhost:8000", "description": "Local direct uvicorn"},
        ],
    )
    app.openapi_schema = openapi_schema
    return openapi_schema


app.openapi = _custom_openapi
