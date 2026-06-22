"""Fetch-error taxonomy for the Role-4 pipeline.

Every exception raised during URL fetching should be mapped to a
:class:`FetchErrorCode` so the error stream is deterministic,
queryable, and dashboard-friendly.
"""

from __future__ import annotations

from enum import Enum

import httpx


class FetchErrorCode(str, Enum):
    """Canonical fetch-error codes used across the Role-4 pipeline."""

    TIMEOUT = "TIMEOUT"
    DNS = "DNS"
    SSL = "SSL"
    STATUS_4XX = "STATUS_4XX"
    STATUS_5XX = "STATUS_5XX"
    PARSE_ERROR = "PARSE_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    BLOCKED = "BLOCKED"
    PROVIDER_DOWN = "PROVIDER_DOWN"
    UNKNOWN = "UNKNOWN"


def _classify_httpx(exc: httpx.HTTPError) -> FetchErrorCode:
    """Map an httpx exception to a :class:`FetchErrorCode`."""
    if isinstance(exc, httpx.TimeoutException):
        return FetchErrorCode.TIMEOUT
    if isinstance(exc, (httpx.ConnectError, httpx.RemoteProtocolError)):
        return FetchErrorCode.DNS
    if isinstance(exc, httpx.ProxyError):
        return FetchErrorCode.DNS
    return FetchErrorCode.UNKNOWN


def classify_fetch_error(exception: Exception, status_code: int | None = None) -> str:
    """Return a ``"{CODE}: {detail}"`` string suitable for ``source.error_message``.

    *exception* is the Python exception caught by the caller.
    *status_code* is the HTTP status (if available).
    """
    if isinstance(exception, httpx.HTTPError):
        code = _classify_httpx(exception)
        return f"{code.name}: {str(exception)[:200]}"
    if status_code is not None:
        if 400 <= status_code < 500:
            if status_code == 429:
                return f"{FetchErrorCode.RATE_LIMITED.name}: HTTP {status_code}"
            if status_code == 403:
                return f"{FetchErrorCode.BLOCKED.name}: HTTP {status_code}"
            return f"{FetchErrorCode.STATUS_4XX.name}: HTTP {status_code}"
        if 500 <= status_code < 600:
            return f"{FetchErrorCode.STATUS_5XX.name}: HTTP {status_code}"
    return f"{FetchErrorCode.UNKNOWN.name}: {str(exception)[:200]}"


def parse_error_code(error_message: str | None) -> str:
    """Extract the ``FetchErrorCode`` name from an ``error_message`` string.

    Returns ``"UNKNOWN"`` when the message is ``None`` or does not start
    with a recognised code name.
    """
    if not error_message:
        return FetchErrorCode.UNKNOWN.name
    first_colon = error_message.find(":")
    prefix = error_message[:first_colon] if first_colon > 0 else error_message
    try:
        return FetchErrorCode(prefix).name
    except ValueError:
        return FetchErrorCode.UNKNOWN.name


__all__ = [
    "FetchErrorCode",
    "classify_fetch_error",
    "parse_error_code",
]
