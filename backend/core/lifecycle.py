"""Application lifecycle hooks.

Centralises start-up validation that used to live (implicitly) inside the
first request to hit the API. Failures here are loud — they raise at
process boot, before any HTTP traffic, so a misconfigured deployment
crashes instead of returning 500s.

Used by ``backend.api.main`` via the FastAPI ``lifespan`` arg.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from backend.core.config import settings

log = logging.getLogger(__name__)


class StartupValidationError(RuntimeError):
    """Raised when one or more required settings fail validation at boot."""


# Required keys that must be present and non-empty.
_REQUIRED_STRING_FIELDS: tuple[str, ...] = (
    "DATABASE_URL",
    "REDIS_URL",
    "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND",
    "QDRANT_URL",
)


def _validate_url(field_name: str, value: str, *, schemes: tuple[str, ...]) -> str:
    """Parse a URL and confirm its scheme is one of the allowed ones."""
    if not value:
        raise StartupValidationError(f"{field_name} is required and must not be empty")
    try:
        parsed = urlparse(value)
    except Exception as exc:
        raise StartupValidationError(
            f"{field_name}={value!r} is not a valid URL: {exc}"
        ) from exc
    if parsed.scheme not in schemes:
        raise StartupValidationError(
            f"{field_name} scheme={parsed.scheme!r} is not in allowed {schemes}"
        )
    if not parsed.netloc:
        raise StartupValidationError(
            f"{field_name}={value!r} is missing host/port"
        )
    return value


def validate_settings() -> dict[str, Any]:
    """Validate the loaded :class:`Settings` instance.

    Returns a small ``summary`` dict the lifespan can log on success.
    Raises :class:`StartupValidationError` (which the caller should
    surface as a clear boot-time error) on the first violation.
    """
    errors: list[str] = []

    for field_name in _REQUIRED_STRING_FIELDS:
        value = getattr(settings, field_name, "") or ""
        if not value.strip():
            errors.append(f"{field_name} is required and must not be empty")

    if errors:
        raise StartupValidationError(
            "Invalid configuration: " + "; ".join(errors)
        )

    # URL-shape validation (only for fields we expect to be URLs).
    try:
        _validate_url("DATABASE_URL", settings.DATABASE_URL, schemes=("postgresql", "postgresql+psycopg"))
    except StartupValidationError as exc:
        errors.append(str(exc))

    try:
        _validate_url("REDIS_URL", settings.REDIS_URL, schemes=("redis", "rediss"))
    except StartupValidationError as exc:
        errors.append(str(exc))

    try:
        _validate_url("CELERY_BROKER_URL", settings.CELERY_BROKER_URL, schemes=("redis", "rediss"))
    except StartupValidationError as exc:
        errors.append(str(exc))

    try:
        _validate_url("CELERY_RESULT_BACKEND", settings.CELERY_RESULT_BACKEND, schemes=("redis", "rediss"))
    except StartupValidationError as exc:
        errors.append(str(exc))

    try:
        _validate_url("QDRANT_URL", settings.QDRANT_URL, schemes=("http", "https"))
    except StartupValidationError as exc:
        errors.append(str(exc))

    if settings.APP_ENV not in {"dev", "staging", "prod"}:
        errors.append(
            f"APP_ENV={settings.APP_ENV!r} is not one of dev|staging|prod"
        )

    if settings.JWT_SECRET_KEY == "change-me-in-production" and settings.APP_ENV == "prod":
        errors.append("JWT_SECRET_KEY must be overridden in prod (still set to default)")

    if errors:
        raise StartupValidationError(
            "Invalid configuration: " + "; ".join(errors)
        )

    summary = {
        "app_env": settings.APP_ENV,
        "log_level": settings.LOG_LEVEL,
        "redis_state_db": settings.REDIS_STATE_DB,
        "score_version": settings.SCORE_VERSION,
    }
    log.info("Startup configuration validated", extra=summary)
    return summary


__all__ = ["StartupValidationError", "validate_settings"]
