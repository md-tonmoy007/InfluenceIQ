"""Tests for fetch-error taxonomy."""

from __future__ import annotations

import httpx
import pytest

from backend.pipeline.content.errors import (
    FetchErrorCode,
    classify_fetch_error,
    parse_error_code,
)


def test_classify_timeout() -> None:
    """httpx.TimeoutException maps to TIMEOUT."""
    exc = httpx.TimeoutException("Connection timed out")
    result = classify_fetch_error(exc)
    assert result.startswith(f"{FetchErrorCode.TIMEOUT.name}:")


def test_classify_dns() -> None:
    """httpx.ConnectError maps to DNS."""
    exc = httpx.ConnectError("Name or service not known")
    result = classify_fetch_error(exc)
    assert result.startswith(f"{FetchErrorCode.DNS.name}:")


def test_classify_ssl() -> None:
    """httpx.ProxyError (a TransportError) maps to DNS. SSL errors are
    also TransportErrors, so they get DNS classification — we document
    this lower-bound in the error taxonomy."""
    exc = httpx.ProxyError("proxy failure")
    result = classify_fetch_error(exc)
    assert result.startswith(f"{FetchErrorCode.DNS.name}:")


def test_classify_unknown_exception() -> None:
    """Arbitrary exceptions without status codes produce UNKNOWN."""
    exc = RuntimeError("something went wrong")
    result = classify_fetch_error(exc)
    assert result.startswith(f"{FetchErrorCode.UNKNOWN.name}:")


def test_classify_status_4xx() -> None:
    """A 4xx status maps to STATUS_4XX."""
    exc = Exception("client error")
    result = classify_fetch_error(exc, status_code=404)
    assert result.startswith(f"{FetchErrorCode.STATUS_4XX.name}:")


def test_classify_status_5xx() -> None:
    """A 5xx status maps to STATUS_5XX."""
    exc = Exception("server error")
    result = classify_fetch_error(exc, status_code=502)
    assert result.startswith(f"{FetchErrorCode.STATUS_5XX.name}:")


def test_classify_rate_limited() -> None:
    """HTTP 429 maps to RATE_LIMITED."""
    exc = Exception("too many requests")
    result = classify_fetch_error(exc, status_code=429)
    assert result.startswith(f"{FetchErrorCode.RATE_LIMITED.name}:")


def test_classify_blocked() -> None:
    """HTTP 403 maps to BLOCKED."""
    exc = Exception("forbidden")
    result = classify_fetch_error(exc, status_code=403)
    assert result.startswith(f"{FetchErrorCode.BLOCKED.name}:")


def test_parse_error_code_extracts_prefix() -> None:
    """parse_error_code extracts the error code prefix."""
    assert parse_error_code("TIMEOUT: connection failed") == "TIMEOUT"
    assert parse_error_code("DNS: name not resolved") == "DNS"
    assert parse_error_code("RATE_LIMITED: HTTP 429") == "RATE_LIMITED"


def test_parse_error_code_none_returns_unknown() -> None:
    """None input returns UNKNOWN."""
    assert parse_error_code(None) == "UNKNOWN"


def test_parse_error_code_unrecognised_returns_unknown() -> None:
    """Unrecognised strings return UNKNOWN."""
    assert parse_error_code("BOGUS: something") == "UNKNOWN"
