"""Tests for the provider circuit breaker.

The circuit breaker uses Redis sorted sets. When Redis is unavailable
the breaker degrades to "always available" (fail-open). These tests
mock the Redis client so they run offline.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.pipeline.content.cache import (
    PROVIDER_COOLDOWN,
    PROVIDER_FAIL_THRESHOLD,
    PROVIDER_FAIL_WINDOW,
    provider_is_available,
    record_provider_failure,
    reset_provider_breaker,
)


def _make_mock_redis() -> MagicMock:
    """Build a mock Redis client with a cooperative pipeline."""
    mock = MagicMock()
    mock.zadd.return_value = 1
    mock.zremrangebyscore.return_value = 0
    mock.expire.return_value = True
    mock.zcard.return_value = 1
    mock.ttl.return_value = -1
    mock.delete.return_value = 1
    # pipeline
    pipeline = MagicMock()
    pipeline.__enter__.return_value = pipeline
    pipeline.zadd.return_value = pipeline
    pipeline.zremrangebyscore.return_value = pipeline
    pipeline.expire.return_value = pipeline
    pipeline.zcard.return_value = pipeline
    pipeline.execute.return_value = (1, 0, True, 1)
    mock.pipeline.return_value = pipeline
    return mock


@patch("backend.pipeline.content.cache.redis_client")
def test_record_failure_below_threshold(mock_redis_client: MagicMock) -> None:
    """Fewer than 5 failures does not open the breaker."""
    mock_redis = _make_mock_redis()
    mock_redis.zcard.return_value = 3
    pipeline = mock_redis.pipeline.return_value
    pipeline.execute.return_value = (1, 0, True, 3)
    mock_redis_client.return_value = mock_redis

    opened = record_provider_failure("youtube")
    assert opened is False


@patch("backend.pipeline.content.cache.redis_client")
def test_record_failure_at_threshold(mock_redis_client: MagicMock) -> None:
    """At threshold (5 failures) the breaker opens."""
    mock_redis = _make_mock_redis()
    mock_redis.zcard.return_value = 5
    pipeline = mock_redis.pipeline.return_value
    pipeline.execute.return_value = (1, 0, True, 5)
    mock_redis_client.return_value = mock_redis

    opened = record_provider_failure("instagram")
    assert opened is True


@patch("backend.pipeline.content.cache.redis_client")
def test_provider_is_available_no_key(mock_redis_client: MagicMock) -> None:
    """Without a fail key the provider is available."""
    mock_redis = _make_mock_redis()
    mock_redis.ttl.return_value = -1  # key doesn't exist
    mock_redis_client.return_value = mock_redis
    assert provider_is_available("youtube") is True


@patch("backend.pipeline.content.cache.redis_client")
def test_provider_is_unavailable_during_cooldown(mock_redis_client: MagicMock) -> None:
    """During cooldown (TTL > 0) the provider is unavailable."""
    mock_redis = _make_mock_redis()
    mock_redis.ttl.return_value = 120  # 2 minutes remaining
    mock_redis_client.return_value = mock_redis
    assert provider_is_available("instagram") is False


def test_generic_fetchers_always_available() -> None:
    """Generic fetchers (web, fallback, httpx) are never circuit-broken."""
    assert provider_is_available("web") is True
    assert provider_is_available("fallback") is True
    assert provider_is_available("httpx") is True


@patch("backend.pipeline.content.cache.redis_client")
def test_reset_breaker(mock_redis_client: MagicMock) -> None:
    """Reset clears the fail key."""
    mock_redis = _make_mock_redis()
    mock_redis_client.return_value = mock_redis
    reset_provider_breaker("youtube")
    mock_redis.delete.assert_called_once_with("role4:provider_fail:youtube")


@patch("backend.pipeline.content.cache.redis_client")
def test_record_failure_redis_error_degrades_gracefully(mock_redis_client: MagicMock) -> None:
    """When Redis is unreachable, record_provider_failure returns False (no open)."""
    import redis
    mock_redis_client.side_effect = redis.ConnectionError("Redis connection refused")

    opened = record_provider_failure("youtube")
    assert opened is False
