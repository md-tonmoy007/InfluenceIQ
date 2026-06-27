"""Tests for environment-aware search provider routing."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

from backend.pipeline.content.contracts import SearchResult
from backend.pipeline.content.search_providers import search_web


class SearchProviderRoutingTest(unittest.TestCase):
    def test_auto_dev_prefers_openserp_over_brave(self) -> None:
        brave_results = [
            SearchResult(url="https://brave.example/a", title="Brave", snippet="b", relevance_score=80, provider="brave"),
        ]
        openserp_results = [
            SearchResult(url="https://openserp.example/a", title="Open", snippet="o", relevance_score=70, provider="openserp"),
        ]
        with (
            patch("backend.pipeline.content.search_providers.settings.APP_ENV", "dev"),
            patch("backend.pipeline.content.search_providers.settings.SEARCH_PROVIDER_MODE", "auto"),
            patch("backend.pipeline.content.search_providers.settings.OPENSERP_URL", "http://openserp:7000"),
            patch("backend.pipeline.content.search_providers.settings.BRAVE_SEARCH_API_KEY", "key"),
            patch("backend.pipeline.content.search_providers._openserp_search", return_value=openserp_results),
            patch("backend.pipeline.content.search_providers._brave_search", return_value=brave_results),
        ):
            results = search_web("nutrition creators", limit=3)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["provider"], "openserp")

    def test_auto_production_prefers_brave_over_openserp(self) -> None:
        brave_results = [
            SearchResult(url="https://brave.example/a", title="Brave", snippet="b", relevance_score=80, provider="brave"),
        ]
        openserp_results = [
            SearchResult(url="https://openserp.example/a", title="Open", snippet="o", relevance_score=70, provider="openserp"),
        ]
        with (
            patch("backend.pipeline.content.search_providers.settings.APP_ENV", "production"),
            patch("backend.pipeline.content.search_providers.settings.SEARCH_PROVIDER_MODE", "auto"),
            patch("backend.pipeline.content.search_providers.settings.OPENSERP_URL", "http://openserp:7000"),
            patch("backend.pipeline.content.search_providers.settings.BRAVE_SEARCH_API_KEY", "key"),
            patch("backend.pipeline.content.search_providers._openserp_search", return_value=openserp_results),
            patch("backend.pipeline.content.search_providers._brave_search", return_value=brave_results),
        ):
            results = search_web("nutrition creators", limit=3)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["provider"], "brave")

    def test_failover_to_next_provider_when_primary_empty(self) -> None:
        brave_results = [
            SearchResult(url="https://brave.example/a", title="Brave", snippet="b", relevance_score=80, provider="brave"),
        ]
        with (
            patch("backend.pipeline.content.search_providers.settings.SEARCH_PROVIDER_MODE", "openserp"),
            patch("backend.pipeline.content.search_providers.settings.OPENSERP_URL", "http://openserp:7000"),
            patch("backend.pipeline.content.search_providers.settings.BRAVE_SEARCH_API_KEY", "key"),
            patch("backend.pipeline.content.search_providers._openserp_search", return_value=[]),
            patch("backend.pipeline.content.search_providers._brave_search", return_value=brave_results),
        ):
            results = search_web("nutrition creators", limit=3)

        self.assertEqual(results[0]["provider"], "brave")


if __name__ == "__main__":
    unittest.main()
