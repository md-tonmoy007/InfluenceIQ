"""Tests for search provider routing."""

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
    def test_auto_prefers_brave(self) -> None:
        brave_results = [
            SearchResult(url="https://brave.example/a", title="Brave", snippet="b", relevance_score=80, provider="brave"),
        ]
        with (
            patch("backend.pipeline.content.search_providers.settings.APP_ENV", "dev"),
            patch("backend.pipeline.content.search_providers.settings.SEARCH_PROVIDER_MODE", "auto"),
            patch("backend.pipeline.content.search_providers.settings.BRAVE_SEARCH_API_KEY", "key"),
            patch("backend.pipeline.content.search_providers._brave_search", return_value=brave_results),
        ):
            results = search_web("nutrition creators", limit=3)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["provider"], "brave")

    def test_failover_to_serpapi_when_brave_empty(self) -> None:
        serp_results = [
            SearchResult(url="https://serpapi.example/a", title="Serp", snippet="s", relevance_score=80, provider="serpapi"),
        ]
        with (
            patch("backend.pipeline.content.search_providers.settings.SEARCH_PROVIDER_MODE", "auto"),
            patch("backend.pipeline.content.search_providers.settings.BRAVE_SEARCH_API_KEY", "key"),
            patch("backend.pipeline.content.search_providers.settings.SERP_API_KEY", "key"),
            patch("backend.pipeline.content.search_providers._brave_search", return_value=[]),
            patch("backend.pipeline.content.search_providers._serp_api_search", return_value=serp_results),
        ):
            results = search_web("nutrition creators", limit=3)

        self.assertEqual(results[0]["provider"], "serpapi")

    def test_serpapi_explicit_mode_prefers_serpapi(self) -> None:
        serp_results = [
            SearchResult(url="https://serpapi.example/a", title="Serp", snippet="s", relevance_score=80, provider="serpapi"),
        ]
        with (
            patch("backend.pipeline.content.search_providers.settings.SEARCH_PROVIDER_MODE", "serpapi"),
            patch("backend.pipeline.content.search_providers.settings.SERP_API_KEY", "key"),
            patch("backend.pipeline.content.search_providers._serp_api_search", return_value=serp_results),
        ):
            results = search_web("nutrition creators", limit=3)

        self.assertEqual(results[0]["provider"], "serpapi")


if __name__ == "__main__":
    unittest.main()
