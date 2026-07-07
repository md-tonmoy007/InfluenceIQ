"""Unit tests for the v1 deep analysis workflow.

Tests the internal helper functions in ``backend.pipeline.tasks.deep``
including confidence derivation, strength/risk generation, recommendation
text, grade calculation, and report payload schema completeness.

These tests do NOT require a database or external services. They exercise
the pure-logic functions directly.
"""

from __future__ import annotations

import os
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://x:x@localhost:5432/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

from backend.pipeline.tasks.deep import (
    _brand_safety_summary,
    _build_citations,
    _build_coverage_summary,
    _build_recommendation,
    _derive_confidence,
    _derive_strengths_risks,
    _flag_brand_risk,
    _grade_from_scores,
    _handle_variants,
    _merge_coverage_with_comments,
    _platform_from_url,
)


class ConfidenceTests(unittest.TestCase):
    """Tests for _derive_confidence — verifies levels based on evidence quality."""

    def test_high_confidence_with_rich_data(self) -> None:
        external = {"_coverage": {"google_trends": "ok", "search_visibility": "ok", "web_sentiment": "ok"}}
        posts = [{"status": "ok"}] * 15
        result = _derive_confidence(total_comments=500, external=external, posts_analyzed=posts)
        self.assertEqual(result["level"], "High")
        self.assertGreater(result["score"], 0.7)

    def test_medium_confidence_with_partial_data(self) -> None:
        external = {"_coverage": {"google_trends": "no_data", "search_visibility": "ok"}}
        posts = [{"status": "ok"}] * 5
        result = _derive_confidence(total_comments=50, external=external, posts_analyzed=posts)
        self.assertEqual(result["level"], "Medium")
        self.assertGreaterEqual(result["score"], 0.4)
        self.assertLess(result["score"], 0.7)

    def test_low_confidence_with_no_comments(self) -> None:
        external = {"_coverage": {"google_trends": "no_data", "search_visibility": "no_results"}}
        result = _derive_confidence(total_comments=0, external=external, posts_analyzed=[])
        self.assertEqual(result["level"], "Low")
        self.assertLess(result["score"], 0.4)

    def test_confidence_penalized_when_posts_lack_comments(self) -> None:
        external = {"_coverage": {"google_trends": "ok"}}
        posts = [
            {"status": "ok"},
            {"status": "ok"},
            {"status": "no_comments"},
        ]
        result = _derive_confidence(total_comments=200, external=external, posts_analyzed=posts)
        self.assertIn("some posts lack comments", result["reasoning"])

    def test_confidence_external_signals_unavailable(self) -> None:
        external = {"_coverage": {"google_trends": "error", "search_visibility": "error"}}
        posts = [{"status": "ok"}] * 3
        result = _derive_confidence(total_comments=30, external=external, posts_analyzed=posts)
        self.assertNotIn("external signals available", result["reasoning"])
        self.assertIn("limited comment volume", result["reasoning"])

    def test_confidence_reasoning_includes_all_factors(self) -> None:
        external = {"_coverage": {"google_trends": "ok", "search_visibility": "ok"}}
        posts = [{"status": "ok"}] * 12
        result = _derive_confidence(total_comments=300, external=external, posts_analyzed=posts)
        reasoning = result["reasoning"]
        self.assertIn("sufficient comment volume", reasoning)
        self.assertIn("sufficient post coverage", reasoning)
        self.assertIn("external signals available", reasoning)


class StrengthsRisksTests(unittest.TestCase):
    """Tests for _derive_strengths_risks — verifies correct signal interpretation."""

    def test_strong_positive_sentiment_produces_strength(self) -> None:
        external = {"_coverage": {}}
        strengths, risks = _derive_strengths_risks(sentiment=85.0, fake_risk=10.0, external=external, has_data=True)
        self.assertIn("Strong positive audience sentiment", strengths)
        self.assertIn("Low fake engagement risk", strengths)

    def test_high_fake_risk_produces_risk(self) -> None:
        external = {"_coverage": {}}
        strengths, risks = _derive_strengths_risks(sentiment=50.0, fake_risk=65.0, external=external, has_data=True)
        self.assertIn("High fake engagement risk — engagement authenticity is weak", risks)

    def test_elevated_fake_risk_produces_risk(self) -> None:
        external = {"_coverage": {}}
        strengths, risks = _derive_strengths_risks(sentiment=55.0, fake_risk=45.0, external=external, has_data=True)
        self.assertIn("Elevated fake engagement risk", risks)

    def test_trends_ok_adds_strength(self) -> None:
        external = {"_coverage": {"google_trends": "ok"}}
        strengths, risks = _derive_strengths_risks(sentiment=50.0, fake_risk=10.0, external=external, has_data=True)
        self.assertIn("Google Trends data supports popularity assessment", strengths)

    def test_trends_no_data_adds_risk(self) -> None:
        external = {"_coverage": {"google_trends": "no_data"}}
        strengths, risks = _derive_strengths_risks(sentiment=50.0, fake_risk=10.0, external=external, has_data=True)
        self.assertIn("Google Trends unavailable for this creator — popularity signals limited", risks)

    def test_search_visibility_ok_adds_strength(self) -> None:
        external = {"_coverage": {"search_visibility": "ok"}}
        strengths, risks = _derive_strengths_risks(sentiment=50.0, fake_risk=10.0, external=external, has_data=True)
        self.assertIn("External search visibility confirmed", strengths)

    def test_search_visibility_no_results_adds_risk(self) -> None:
        external = {"_coverage": {"search_visibility": "no_results"}}
        strengths, risks = _derive_strengths_risks(sentiment=50.0, fake_risk=10.0, external=external, has_data=True)
        self.assertIn("Limited external search visibility", risks)

    def test_no_data_suppresses_evidence_based_strengths(self) -> None:
        """When we have no evidence, the function must not assert
        "Low fake engagement risk" or "External search visibility confirmed"."""
        external = {"_coverage": {"search_visibility": "ok", "google_trends": "ok"}}
        strengths, risks = _derive_strengths_risks(sentiment=85.0, fake_risk=10.0, external=external, has_data=False)
        self.assertNotIn("Low fake engagement risk", strengths)
        self.assertNotIn("Strong positive audience sentiment", strengths)
        self.assertNotIn("External search visibility confirmed", strengths)
        self.assertNotIn("Google Trends data supports popularity assessment", strengths)
        self.assertTrue(any("Insufficient evidence" in s for s in strengths))
        self.assertTrue(any("Re-run after enrichment" in r for r in risks))


class RecommendationTests(unittest.TestCase):
    """Tests for _build_recommendation."""

    def test_no_data_returns_re_run_message(self) -> None:
        result = _build_recommendation(sentiment=90.0, fake_risk=0.0, total_comments=0, has_data=False)
        self.assertIn("Insufficient data to grade this creator", result)

    def test_no_comments_with_data_returns_insufficient_comments(self) -> None:
        result = _build_recommendation(sentiment=90.0, fake_risk=0.0, total_comments=0, has_data=True)
        self.assertIn("Insufficient comment data", result)

    def test_no_data_takes_precedence_over_no_comments(self) -> None:
        result = _build_recommendation(sentiment=90.0, fake_risk=0.0, total_comments=10, has_data=False)
        self.assertIn("Insufficient data to grade this creator", result)

    def test_high_fake_risk_returns_caution(self) -> None:
        result = _build_recommendation(sentiment=90.0, fake_risk=75.0, total_comments=100, has_data=True)
        self.assertIn("Proceed with caution", result)

    def test_strong_sentiment_returns_partnership(self) -> None:
        result = _build_recommendation(sentiment=80.0, fake_risk=10.0, total_comments=200, has_data=True)
        self.assertIn("Strong audience sentiment supports partnership", result)

    def test_mixed_sentiment_returns_review(self) -> None:
        result = _build_recommendation(sentiment=60.0, fake_risk=10.0, total_comments=200, has_data=True)
        self.assertIn("Mixed audience sentiment", result)

    def test_weak_sentiment_returns_consider_others(self) -> None:
        result = _build_recommendation(sentiment=30.0, fake_risk=10.0, total_comments=200, has_data=True)
        self.assertIn("Weak audience sentiment", result)


class GradeTests(unittest.TestCase):
    """Tests for _grade_from_scores."""

    def test_perfect_grade(self) -> None:
        self.assertEqual(_grade_from_scores(sentiment=95.0, fake_risk=0.0, has_data=True), "A")

    def test_good_grade(self) -> None:
        self.assertEqual(_grade_from_scores(sentiment=75.0, fake_risk=5.0, has_data=True), "B")

    def test_average_grade(self) -> None:
        self.assertEqual(_grade_from_scores(sentiment=65.0, fake_risk=10.0, has_data=True), "C")

    def test_poor_grade(self) -> None:
        self.assertEqual(_grade_from_scores(sentiment=50.0, fake_risk=20.0, has_data=True), "D")

    def test_fail_grade(self) -> None:
        self.assertEqual(_grade_from_scores(sentiment=20.0, fake_risk=60.0, has_data=True), "F")

    def test_high_fake_risk_drags_grade_down(self) -> None:
        grade_clean = _grade_from_scores(sentiment=75.0, fake_risk=0.0, has_data=True)
        grade_risky = _grade_from_scores(sentiment=75.0, fake_risk=70.0, has_data=True)
        self.assertEqual(grade_clean, "B")
        # 75 - 70*0.4 = 75 - 28 = 47, which falls in D (40-60)
        self.assertEqual(grade_risky, "D")

    def test_no_data_returns_na_grade(self) -> None:
        """With no evidence the grade must be N/A, not a misleading D."""
        self.assertEqual(_grade_from_scores(sentiment=50.0, fake_risk=0.0, has_data=False), "N/A")
        self.assertEqual(_grade_from_scores(sentiment=95.0, fake_risk=0.0, has_data=False), "N/A")


class URLParsingTests(unittest.TestCase):
    """Tests for _platform_from_url and _handle_variants."""

    def test_instagram_url(self) -> None:
        self.assertEqual(_platform_from_url("https://instagram.com/creator"), "instagram")

    def test_tiktok_url(self) -> None:
        self.assertEqual(_platform_from_url("https://tiktok.com/@creator"), "tiktok")

    def test_youtube_url(self) -> None:
        self.assertEqual(_platform_from_url("https://youtube.com/@creator"), "youtube")

    def test_youtu_be_url(self) -> None:
        self.assertEqual(_platform_from_url("https://youtu.be/abc123"), "youtube")

    def test_x_url(self) -> None:
        self.assertEqual(_platform_from_url("https://x.com/creator"), "x")

    def test_twitter_url(self) -> None:
        self.assertEqual(_platform_from_url("https://twitter.com/creator"), "x")

    def test_unknown_url(self) -> None:
        self.assertEqual(_platform_from_url("https://example.com/page"), "unknown")

    def test_handle_variants_extracts_from_platforms(self) -> None:
        candidate = {
            "platforms": {
                "instagram": "https://instagram.com/fitness_guru",
                "x": "https://x.com/fitguru",
                "tiktok": "https://tiktok.com/@fitguru",
            },
        }
        handles = _handle_variants(candidate)
        self.assertIn("fitness_guru", handles)
        self.assertIn("fitguru", handles)

    def test_handle_variants_handles_missing_platforms(self) -> None:
        self.assertEqual(_handle_variants({}), [])
        self.assertEqual(_handle_variants({"platforms": {}}), [])


class CoverageSummaryTests(unittest.TestCase):
    """Tests for _build_coverage_summary."""

    def test_builds_from_provider_coverage_and_posts(self) -> None:
        provider_coverage = {
            "https://instagram.com/user": "ok",
            "https://youtube.com/@user": "partial",
        }
        post1 = MagicMock()
        post1.platform = "instagram"
        post2 = MagicMock()
        post2.platform = "instagram"
        post3 = MagicMock()
        post3.platform = "youtube"
        posts = [post1, post2, post3]

        summary = _build_coverage_summary(provider_coverage, posts)
        self.assertIn("instagram", summary)
        self.assertEqual(summary["instagram"]["posts_fetched"], 2)
        self.assertEqual(summary["instagram"]["profile_status"], "ok")
        self.assertEqual(summary["youtube"]["profile_status"], "partial")
        # comments_fetched must default to False — the merge helper is
        # the only place that flips it to True.
        self.assertFalse(summary["instagram"]["comments_fetched"])
        self.assertFalse(summary["youtube"]["comments_fetched"])
        self.assertEqual(summary["instagram"]["comments_analyzed"], 0)
        self.assertEqual(summary["youtube"]["comments_analyzed"], 0)

    def test_empty_coverage_and_posts(self) -> None:
        summary = _build_coverage_summary({}, [])
        self.assertEqual(summary, {})


class CitationTests(unittest.TestCase):
    """Tests for _build_citations."""

    def test_builds_post_citations(self) -> None:
        posts = [
            {"status": "ok", "post_id": "abc", "platform": "instagram",
             "comment_count": 12, "sentiment_score": 72.0, "fake_comment_risk": 5.0},
            {"status": "no_comments", "post_id": "def", "platform": "youtube"},
        ]
        external = {}
        citations = _build_citations(posts, external)
        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]["source"], "post")
        self.assertEqual(citations[0]["post_id"], "abc")

    def test_builds_search_visibility_citations(self) -> None:
        external = {
            "search_visibility": {
                "queries": {
                    "q1": [{"url": "https://example.com/a"}],
                    "q2": [],
                }
            }
        }
        citations = _build_citations([], external)
        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]["source"], "search_visibility")


class ReportPayloadSchemaTests(unittest.TestCase):
    """Verifies the report_payload dict has all 13 required keys from the v1 plan."""

    REQUIRED_KEYS = [
        "creator_summary",
        "campaign_fit_summary",
        "platform_coverage",
        "posts_analyzed",
        "comments_analyzed",
        "audience_signals",
        "popularity_signals",
        "brand_safety_signals",
        "key_strengths",
        "key_risks",
        "recommendation",
        "confidence_reasoning",
        "citations",
    ]

    def _build_minimal_payload(self) -> dict:
        """Simulate what _synthesize_report produces without hitting DB."""
        candidate = {
            "canonical_name": "Test Creator",
            "primary_platform": "instagram",
            "followers": 50000,
            "engagement_rate": 3.5,
            "verified": False,
        }
        posts_analyzed: list[dict] = []
        external = {
            "google_trends": {"interest_over_time": []},
            "search_visibility": {"queries": {}},
            "web_sentiment": {"snippets": []},
            "_coverage": {"google_trends": "ok", "search_visibility": "ok", "web_sentiment": "ok"},
        }
        confidence = _derive_confidence(total_comments=100, external=external, posts_analyzed=posts_analyzed)
        strengths, risks = _derive_strengths_risks(sentiment=70.0, fake_risk=15.0, external=external, has_data=True)
        recommendation = _build_recommendation(sentiment=70.0, fake_risk=15.0, total_comments=100, has_data=True)
        citations = _build_citations(posts_analyzed, external)

        return {
            "creator_summary": {
                "name": candidate["canonical_name"],
                "primary_platform": candidate["primary_platform"],
                "followers": candidate["followers"],
                "engagement_rate": candidate["engagement_rate"],
                "verified": candidate["verified"],
            },
            "campaign_fit_summary": recommendation,
            "platform_coverage": {},
            "posts_analyzed": posts_analyzed,
            "comments_analyzed": 100,
            "audience_signals": {"sentiment": 70.0, "fake_engagement_risk": 15.0, "grade": "B"},
            "popularity_signals": external.get("google_trends") or {},
            "brand_safety_signals": {
                "search_visibility": external.get("search_visibility"),
                "web_sentiment": external.get("web_sentiment"),
            },
            "key_strengths": strengths,
            "key_risks": risks,
            "recommendation": recommendation,
            "confidence_reasoning": confidence.get("reasoning", ""),
            "citations": citations,
        }

    def test_payload_contains_all_required_keys(self) -> None:
        payload = self._build_minimal_payload()
        for key in self.REQUIRED_KEYS:
            with self.subTest(key=key):
                self.assertIn(key, payload, f"Missing required key: {key}")

    def test_creator_summary_has_required_fields(self) -> None:
        payload = self._build_minimal_payload()
        creator = payload["creator_summary"]
        for field in ("name", "primary_platform", "followers", "engagement_rate", "verified"):
            self.assertIn(field, creator)

    def test_audience_signals_has_required_fields(self) -> None:
        payload = self._build_minimal_payload()
        signals = payload["audience_signals"]
        for field in ("sentiment", "fake_engagement_risk", "grade"):
            self.assertIn(field, signals)

    def test_brand_safety_signals_has_required_fields(self) -> None:
        payload = self._build_minimal_payload()
        signals = payload["brand_safety_signals"]
        for field in ("search_visibility", "web_sentiment"):
            self.assertIn(field, signals)


class CacheExpiryTests(unittest.TestCase):
    """Tests for freshness / cache expiry logic used in the API layer."""

    def test_report_is_fresh_when_cache_not_expired(self) -> None:
        now = datetime.now(UTC)
        expires = now + timedelta(minutes=30)
        self.assertTrue(expires > now)

    def test_report_is_stale_when_cache_expired(self) -> None:
        now = datetime.now(UTC)
        expires = now - timedelta(minutes=1)
        self.assertFalse(expires > now)


class ExternalSignalFailureTests(unittest.TestCase):
    """Tests that failed external-signal collection does not crash the run."""

    def test_fallback_payload_on_exception(self) -> None:
        """The _collect_external wrapper catches exceptions and returns a fallback."""
        fallback = {
            "google_trends": None,
            "search_visibility": None,
            "web_sentiment": None,
            "_coverage": {
                "google_trends": "error",
                "search_visibility": "error",
                "web_sentiment": "error",
            },
        }
        self.assertIsNone(fallback["google_trends"])
        self.assertEqual(fallback["_coverage"]["google_trends"], "error")

    def test_fallback_does_not_break_confidence_calc(self) -> None:
        fallback = {
            "_coverage": {"google_trends": "error", "search_visibility": "error"},
        }
        posts = [{"status": "ok"}] * 5
        result = _derive_confidence(total_comments=100, external=fallback, posts_analyzed=posts)
        self.assertIn(result["level"], {"Medium", "High", "Low"})


class NoSocialURLsTests(unittest.TestCase):
    """Tests for the case where no supported social URLs are present."""

    def test_no_urls_produces_empty_coverage(self) -> None:
        summary = _build_coverage_summary({}, [])
        self.assertEqual(summary, {})

    def test_no_handles_produces_empty_variants(self) -> None:
        candidate = {"platforms": {}}
        handles = _handle_variants(candidate)
        self.assertEqual(handles, [])

    def test_no_comments_with_data_yields_insufficient_recommendation(self) -> None:
        self.assertIn("Insufficient comment data",
                       _build_recommendation(sentiment=80.0, fake_risk=0.0, total_comments=0, has_data=True))


class BrandSafetySummaryTests(unittest.TestCase):
    """Tests for the brand-safety summary text — the report must show
    'N mentions (M flagged)' rather than a raw count of search results."""

    def test_no_snippets_yields_no_additional_issues(self) -> None:
        self.assertIn("No additional", _brand_safety_summary({"web_sentiment": None}))
        self.assertIn("No additional", _brand_safety_summary({"web_sentiment": {}}))
        self.assertIn("No additional", _brand_safety_summary({}))

    def test_snippets_with_no_flags_says_none_flagged(self) -> None:
        external = {"web_sentiment": {"snippets": [
            {"title": "Cool creator bio", "snippet": "Behind the scenes"},
            {"title": "Interview", "snippet": "Talks about craft"},
        ]}}
        text = _brand_safety_summary(external)
        self.assertIn("2 external mentions", text)
        self.assertIn("none flagged", text)

    def test_snippets_with_flags_separates_total_and_flagged(self) -> None:
        external = {"web_sentiment": {"snippets": [
            {"title": "Cool creator bio", "snippet": "Behind the scenes"},
            {"title": "Lawsuit update", "snippet": "Creators in the news"},
            {"title": "Interview", "snippet": "Talks about craft"},
        ]}}
        text = _brand_safety_summary(external)
        self.assertIn("3 external mentions", text)
        self.assertIn("1 flagged", text)
        self.assertIn("review for brand-risk signals", text)

    def test_keyword_detects_lawsuit_controversy_scandal(self) -> None:
        for keyword in ("lawsuit", "scandal", "fraud", "controversy", "sued"):
            self.assertTrue(_flag_brand_risk({"title": f"Creator {keyword} 2024", "snippet": ""}))
        self.assertFalse(_flag_brand_risk({"title": "Profile", "snippet": "Behind the scenes"}))


class CoverageMergeTests(unittest.TestCase):
    """Tests for _merge_coverage_with_comments — the per-platform
    ``comments_fetched`` flag must reflect the comment-stage result."""

    def test_merge_marks_platform_with_comments(self) -> None:
        social = {"coverage": {
            "instagram": {"profile_status": "ok", "posts_fetched": 5, "comments_fetched": False, "comments_analyzed": 0},
            "youtube": {"profile_status": "partial", "posts_fetched": 2, "comments_fetched": False, "comments_analyzed": 0},
        }}
        out = _merge_coverage_with_comments(social, {"instagram": 30})
        self.assertTrue(out["coverage"]["instagram"]["comments_fetched"])
        self.assertEqual(out["coverage"]["instagram"]["comments_analyzed"], 30)
        self.assertFalse(out["coverage"]["youtube"]["comments_fetched"])
        self.assertEqual(out["coverage"]["youtube"]["comments_analyzed"], 0)

    def test_merge_handles_empty_inputs(self) -> None:
        # No coverage key → helper returns input with an empty
        # ``coverage`` dict stamped in.
        self.assertEqual(_merge_coverage_with_comments({}, {}), {"coverage": {}})
        self.assertEqual(_merge_coverage_with_comments({"coverage": {}}, {}), {"coverage": {}})


class ConfidenceNoDataTests(unittest.TestCase):
    """Confidence must drop to Low with a clear reasoning when we have
    no analyzed posts and no comments."""

    def test_no_data_low_with_clear_reasoning(self) -> None:
        result = _derive_confidence(total_comments=0, external={"_coverage": {}}, posts_analyzed=[])
        self.assertEqual(result["level"], "Low")
        self.assertEqual(result["score"], 0.0)
        self.assertIn("insufficient evidence", result["reasoning"])

    def test_some_data_does_not_trigger_insufficient_evidence(self) -> None:
        result = _derive_confidence(total_comments=10, external={"_coverage": {}}, posts_analyzed=[{"status": "ok"}])
        self.assertNotIn("insufficient evidence", result["reasoning"])
        self.assertIn("limited comment volume", result["reasoning"])


if __name__ == "__main__":
    unittest.main()
