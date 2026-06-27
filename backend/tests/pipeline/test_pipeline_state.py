from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.core.cache.pipeline_state import increment_pipeline_counter, initialize_pipeline_state


def test_increment_pipeline_counter_is_atomic():
    fake_redis = MagicMock()
    fake_redis.hincrby.side_effect = [1, 1, 2, 2]

    with patch("backend.core.cache.pipeline_state.redis_client", fake_redis):
        initialize_pipeline_state("test-campaign-counter")
        assert increment_pipeline_counter("test-campaign-counter", "urls_scraped") == 1
        assert increment_pipeline_counter("test-campaign-counter", "urls_scraped") == 2
        assert fake_redis.hincrby.call_count >= 4
