"""Global exception handlers + error envelope wiring.

Registered on the FastAPI app in :mod:`backend.api.main`. Every handler
returns an :class:`ErrorEnvelope` shape so clients have one parser.

The handlers do not raise the original exception — they translate it
into a structured response. The middleware (request_logging) still
sees the exception via its ``call_next`` path and logs it.

Custom codes used by the app:

* ``validation_error`` — pydantic request validation failed
* ``http_error``      — :class:`HTTPException` raised by a handler
* ``not_found``       — convenience alias for 404
* ``conflict``        — convenience alias for 409 (idempotency violation)
* ``server_error``    — unhandled exception; details are redacted
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.api.schemas.errors import ErrorBody, ErrorDetail, ErrorEnvelope

log = structlog.get_logger()


def _envelope(code: str, message: str, details: list[ErrorDetail] | None = None, request_id: str | None = None) -> dict[str, Any]:
    body = ErrorBody(
        code=code, message=message, details=details or [], request_id=request_id
    )
    return ErrorEnvelope(error=body).model_dump(mode="json")


def _request_id(request: Request) -> str | None:
    """Read the X-Request-ID header that the logging middleware set."""
    return request.headers.get("X-Request-ID") or None


def register_error_handlers(app: FastAPI) -> None:
    """Attach all custom handlers to ``app``.

    Idempotent — calling twice will simply register the same handler
    twice (FastAPI dedups by reference so it's a no-op the second time).
    """

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        details: list[ErrorDetail] = []
        for err in exc.errors():
            loc = ".".join(str(part) for part in err.get("loc", []))
            details.append(
                ErrorDetail(
                    field=loc or None,
                    issue=err.get("msg", "validation error"),
                    code=err.get("type"),
                )
            )
        message = f"{len(details)} validation error{'s' if len(details) != 1 else ''}"
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_envelope("validation_error", message, details, _request_id(request)),
        )

    @app.exception_handler(HTTPException)
    async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        code_map = {
            400: "bad_request",
            401: "unauthenticated",
            403: "forbidden",
            404: "not_found",
            409: "conflict",
            429: "rate_limited",
        }
        code = code_map.get(exc.status_code, "http_error")
        # ``detail`` may be a string (default) or a structured dict.
        message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(code, message, request_id=_request_id(request)),
            headers=exc.headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _starlette_http_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Same as the FastAPI HTTPException handler but for raw Starlette
        # errors raised by middleware (e.g. CORS, trusted hosts).
        code = "http_error"
        message = str(exc.detail) if exc.detail else "HTTP error"
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(code, message, request_id=_request_id(request)),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        # Log the full exception server-side; surface a generic message.
        log.exception("unhandled_exception", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope(
                "server_error",
                "An internal error occurred. Check the server logs.",
                request_id=_request_id(request),
            ),
        )


__all__ = ["register_error_handlers"]
