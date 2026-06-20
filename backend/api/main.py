from __future__ import annotations

import structlog
from fastapi import FastAPI

from backend.api.middleware.cors import setup_cors
from backend.api.middleware.request_logging import setup_logging_middleware
from backend.api.routers import campaigns, demo, health, influencers, websocket
from backend.core.config import settings

# Initialize structlog configuration
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer() if settings.APP_ENV == "prod" else structlog.processors.KeyValueRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Create FastAPI instance
app = FastAPI(
    title="InfluenceIQ",
    description="Trust-Aware Influencer Discovery Platform Backend",
    version="0.1.0",
)

# Setup CORS and Custom Logging middleware
setup_cors(app)
setup_logging_middleware(app)

# Register endpoints routers
app.include_router(health.router)
app.include_router(campaigns.router)
app.include_router(influencers.router)
app.include_router(demo.router)
app.include_router(websocket.router)


@app.get("/")
def root() -> dict[str, str]:
    """Service description endpoint."""
    return {
        "service": "InfluenceIQ Backend API",
        "version": app.version,
        "environment": settings.APP_ENV,
        "docs_url": "/docs"
    }
