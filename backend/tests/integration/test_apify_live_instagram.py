"""Integration tests that hit real third-party APIs.

These tests are **skipped automatically** when the corresponding API key is not
present in the environment. They exist to catch regressions like the
"docker compose restart does not re-read env_file" footgun, where the code
path looks correct but the worker process is silently running with an empty
token and falling back to the cheap provider.

Run only when explicitly desired:

    pytest backend/tests/integration/test_apify_live_instagram.py -v

The test is a *live* call (not a mock) so it costs a fraction of a cent in
Apify credits. Keep the number of handles exercised small.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

# Ensure project root is importable when pytest is invoked from anywhere.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# The provider does not need a DB, but backend.core.config requires these
# to be set; using harmless defaults keeps the import path side-effect free.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

from backend.core.config import settings  # noqa: E402
from backend.pipeline.content.providers.instagram import fetch_instagram_profile  # noqa: E402

_TOKEN_SET = bool(settings.APIFY_API_TOKEN)
_SKIP_REASON = (
    "APIFY_API_TOKEN is not set in the current process environment. "
    "Set it in backend/.env and (re)start the worker with "
    "`docker compose up -d worker_scraping` to enable this live test."
)


@unittest.skipUnless(_TOKEN_SET, _SKIP_REASON)
class ApifyLiveInstagramTest(unittest.TestCase):
    """Hits the real Apify Instagram profile scraper and asserts the worker
    code path populates the rich profile fields (followers, posts with
    likes/views, verified). Uses the official @instagram handle because
    it is stable, public, and unlikely to be deleted."""

    HANDLE_URL = "https://www.instagram.com/instagram/"

    def test_apify_token_is_non_empty_string(self) -> None:
        # Defensive: a "set" env var can still be the empty string. The
        # provider treats both as "no token" and falls back. Catching this
        # here is the whole point of the regression test.
        self.assertTrue(settings.APIFY_API_TOKEN, "APIFY_API_TOKEN is empty in this process")
        self.assertTrue(
            settings.APIFY_API_TOKEN.startswith("apify_api_"),
            f"APIFY_API_TOKEN does not look like an Apify token (got prefix "
            f"{settings.APIFY_API_TOKEN[:8]!r}). Did you paste the wrong key?",
        )

    def test_fetch_instagram_profile_uses_apify_provider(self) -> None:
        profile = fetch_instagram_profile(self.HANDLE_URL)
        self.assertIsNotNone(
            profile,
            "fetch_instagram_profile returned None — Apify actor run failed "
            "or returned no items. Check the network egress and actor id.",
        )
        self.assertEqual(
            profile.provider,
            "apify_instagram",
            f"provider is {profile.provider!r}, expected 'apify_instagram'. "
            "This means the worker fell back to the meta tags or web API path "
            "because Apify was not actually called — usually because "
            "APIFY_API_TOKEN is empty in the worker process (see doc note: "
            "use `docker compose up -d` not `docker compose restart`).",
        )

    def test_apify_profile_has_rich_fields(self) -> None:
        profile = fetch_instagram_profile(self.HANDLE_URL)
        self.assertIsNotNone(profile)
        # @instagram has 600M+ followers; anything < 1M means the actor
        # returned a stub or a different field shape.
        self.assertIsNotNone(profile.followers, "followers missing")
        self.assertGreater(
            profile.followers,
            1_000_000,
            f"followers={profile.followers} is implausibly low for @instagram",
        )
        self.assertTrue(profile.verified, "@instagram should be verified")
        self.assertGreaterEqual(
            len(profile.posts), 1, "no posts returned — actor likely returned wrong shape"
        )
        first = profile.posts[0]
        # At least one of likes/views should be populated.
        self.assertTrue(
            first.get("likes") is not None or first.get("views") is not None,
            f"first post has neither likes nor views: {first}",
        )
        self.assertIsNone(
            profile.error,
            f"profile.error is set: {profile.error!r} — Apify returned a payload "
            "the parser could not interpret.",
        )


if __name__ == "__main__":
    unittest.main()
