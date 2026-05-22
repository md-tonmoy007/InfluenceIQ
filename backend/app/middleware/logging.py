from __future__ import annotations

import time
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Starlette/FastAPI middleware for request performance logging.
    Records request path, HTTP method, client IP, processing time, and status codes.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        structlog.contextvars.clear_contextvars()
        
        # Capture basic request details
        request_id = request.headers.get("X-Request-ID", "")
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else "unknown",
        )

        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            process_time_ms = (time.perf_counter() - start_time) * 1000.0
            
            logger.info(
                "Request processed successfully",
                status_code=response.status_code,
                duration_ms=round(process_time_ms, 2),
            )
            return response
            
        except Exception as e:
            process_time_ms = (time.perf_counter() - start_time) * 1000.0
            logger.exception(
                "Request processing failed",
                error=str(e),
                duration_ms=round(process_time_ms, 2),
            )
            raise e


def setup_logging_middleware(app: FastAPI) -> None:
    """Helper function to register logging middleware with the FastAPI application."""
    app.add_middleware(LoggingMiddleware)
