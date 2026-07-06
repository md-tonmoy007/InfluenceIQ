from __future__ import annotations

import os
import unittest
from html.parser import HTMLParser
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

from backend.pipeline.analysis.brand_safety_blocklist import brand_safety_score, scan_brand_safety
from backend.pipeline.analysis.credibility import calculate_credibility
from backend.pipeline.analysis.fake_engagement import analyze_fake_engagement
from backend.pipeline.analysis.sentiment import analyze_sentiment
from backend.pipeline.extraction.entities import extract_influencer_mentions
from backend.pipeline.extraction.handles import normalize_profile_url
from backend.pipeline.fusion.sub_scores import build_sub_scores
from backend.pipeline.identity.resolver import resolve_candidates, resolve_identity_clusters

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


class FixtureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.links: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.text.append(data.strip())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for name, value in attrs:
            if name == "href" and value:
                self.links.append(value)


def fixture_page(name: str) -> dict:
    parser = FixtureParser()
    parser.feed((FIXTURES / name).read_text(encoding="utf-8"))
    return {
        "url": f"https://source.example/{name}",
        "content": " ".join(parser.text),
        "social_links": parser.links,
    }


class ExtractionTest(unittest.TestCase):
    def test_extracts_names_credentials_titles_and_profiles(self) -> None:
        mentions = extract_influencer_mentions(fixture_page("creator_nutrition.html"))

        self.assertGreaterEqual(len(mentions), 1)
        sarah = next(mention for mention in mentions if "Sarah Tan" in mention["name"])
        self.assertEqual(sarah["platforms"]["instagram"], "https://instagram.com/drsarahtan")
        self.assertEqual(sarah["platforms"]["youtube"], "https://youtube.com/@drsarahtan")
        self.assertIn("MD", sarah["credentials"])
        self.assertIn("Certified Nutritionist", sarah["credentials"])
        self.assertIn("nutritionist", sarah["professional_titles"])

    def test_falls_back_to_handle_when_no_person_name_exists(self) -> None:
        mentions = extract_influencer_mentions(fixture_page("creator_handle_only.html"))

        self.assertEqual(mentions[0]["name"], "@trailwithmaya")
        self.assertEqual(mentions[0]["platforms"], {"instagram": "@trailwithmaya"})

    def test_profile_urls_are_canonicalized(self) -> None:
        self.assertEqual(
            normalize_profile_url("https://www.tiktok.com/@runwithjordan/?lang=en"),
            "https://tiktok.com/@runwithjordan",
        )
        self.assertEqual(normalize_profile_url("twitter.com/AlexStone/"), "https://x.com/AlexStone")


class IdentityTest(unittest.TestCase):
    def test_exact_profile_url_match_is_pass_one(self) -> None:
        decision = resolve_candidates(
            {"name": "Dr Sarah Tan", "platforms": {"instagram": "https://instagram.com/drsarahtan/"}},
            {"name": "Sarah Tan MD", "platforms": {"instagram": "https://www.instagram.com/drsarahtan"}},
        )

        self.assertTrue(decision["merge"])
        self.assertEqual(decision["strategy"], "profile_url")
        self.assertEqual(decision["confidence"], 1.0)
        self.assertEqual(decision["canonical"]["canonical_name"], "Dr Sarah Tan")

    def test_fuzzy_match_merges_same_name(self) -> None:
        decision = resolve_candidates(
            {"name": "Sarah Tan MD", "platforms": {"instagram": "@sarahtanfit"}},
            {"name": "Dr Sarah Tan", "platforms": {"youtube": "https://youtube.com/@sarahtanfit"}},
        )

        self.assertTrue(decision["merge"])
        self.assertGreaterEqual(decision["confidence"], 0.85)

    def test_ambiguous_match_is_marked_for_llm(self) -> None:
        decision = resolve_candidates(
            {"name": "Maya Green", "platforms": {"instagram": "@mayagreen"}},
            {"name": "Maya Grant", "platforms": {"youtube": "@grantoutdoors"}},
        )

        self.assertFalse(decision["merge"])
        self.assertTrue(decision["requires_llm"])

    def test_unrelated_candidates_remain_separate(self) -> None:
        decision = resolve_candidates({"name": "Lila Park"}, {"name": "Jordan Chen"})
        self.assertFalse(decision["merge"])
        self.assertFalse(decision["requires_llm"])

    def test_collection_resolution_builds_canonical_records(self) -> None:
        result = resolve_identity_clusters(
            [
                {"name": "Dr Sarah Tan", "platforms": {"instagram": "https://instagram.com/drsarahtan"}},
                {"name": "Sarah Tan MD", "platforms": {"instagram": "https://instagram.com/drsarahtan/"}},
                {"name": "Jordan Chen", "platforms": {"youtube": "https://youtube.com/@runwithjordan"}},
            ]
        )

        self.assertEqual(len(result["canonical"]), 2)
        sarah = next(record for record in result["canonical"] if "Sarah Tan" in record.get("canonical_name", ""))
        self.assertEqual(len(sarah["mentions"]), 2)


class AnalysisTest(unittest.TestCase):
    def test_fake_engagement_uses_documented_weighting(self) -> None:
        result = analyze_fake_engagement(
            ["Amazing", "Amazing", "Nice", "Helpful detailed review"],
            followers=1_000_000,
            average_engagement=1_000,
        )

        expected = (
            result["spam_ratio"] * 0.4
            + result["engagement_mismatch"] * 0.4
            + result["generic_comment_ratio"] * 0.2
        )
        self.assertAlmostEqual(result["bot_probability"], expected, places=3)
        self.assertLess(result["engagement_quality"], 70)

    def test_sentiment_returns_normalized_score(self) -> None:
        positive = analyze_sentiment(["Helpful and authentic", "Excellent professional advice"])
        negative = analyze_sentiment(["This is misleading", "Terrible scam"])
        self.assertGreater(positive["sentiment_score"], 50)
        self.assertLess(negative["sentiment_score"], 50)

    def test_brand_safety_is_auditable(self) -> None:
        page = fixture_page("creator_risky.html")
        result = scan_brand_safety(page["content"], page["url"])

        self.assertTrue(result["risks"]["scam"])
        self.assertTrue(result["risks"]["misinformation"])
        self.assertTrue(result["requires_llm_review"])
        self.assertEqual(brand_safety_score(result["risks"]), 50.0)
        self.assertEqual(result["source_url"], page["url"])

    def test_credibility_rules_and_sparse_data_cap(self) -> None:
        result = calculate_credibility(
            verified=True,
            professional_titles=["dietitian"],
            authority_mentions=1,
            credentials=["RD"],
            sentiment_score=80,
            engagement_quality=90,
            data_source_count=2,
        )

        self.assertEqual(result["credibility_score"], 70.0)
        self.assertTrue(result["confidence_capped"])
        self.assertTrue(any("fewer than 3 sources" in reason for reason in result["reasons"]))

    def test_sub_score_builder_produces_final_formula_inputs(self) -> None:
        result = build_sub_scores(
            {
                "context": "Certified running coach focused on trail training and outdoor education.",
                "professional_titles": ["coach"],
                "credentials": ["Certified Running Coach"],
                "comments": ["Helpful and authentic", "Excellent advice"],
                "followers": 100_000,
                "average_engagement": 5_000,
                "data_source_count": 4,
            },
            {"description": "Outdoor fitness", "interests": ["trail", "running"]},
        )

        self.assertEqual(
            set(result["sub_scores"]),
            {"relevance", "credibility", "engagement", "sentiment", "brand_safety", "data_source_count"},
        )
        for name in ("relevance", "credibility", "engagement", "sentiment", "brand_safety"):
            self.assertGreaterEqual(result["sub_scores"][name], 0)
            self.assertLessEqual(result["sub_scores"][name], 100)


if __name__ == "__main__":
    unittest.main()
