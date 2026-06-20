from pathlib import Path

from backend.pipeline.extraction.credentials import extract_credentials
from backend.pipeline.extraction.entities import extract_influencer_mentions
from backend.pipeline.extraction.handles import extract_handles, normalize_profile_url
from backend.pipeline.extraction.social_urls import extract_social_urls

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def page(name: str) -> dict:
    return {"url": f"https://source.test/{name}", "html": (FIXTURES / name).read_text(encoding="utf-8")}


def test_handle_profile_and_credential_extraction() -> None:
    assert extract_handles("See @alpha and @beta") == ["@alpha", "@beta"]
    assert extract_credentials("Dr Tan MD is a Certified Nutritionist") == ["MD", "Certified Nutritionist"]
    assert extract_social_urls(links=["https://www.instagram.com/alpha/?utm_source=x"])["instagram"] == "https://instagram.com/alpha"


def test_html_fixtures_and_spacy_optional_fallback() -> None:
    for name in ("nutrition.html", "fitness.html", "researcher.html", "handle_only.html", "risky.html"):
        assert extract_influencer_mentions(page(name))
    assert extract_influencer_mentions(page("handle_only.html"))[0]["name"] == "@trailwithmaya"


def test_url_normalization() -> None:
    assert normalize_profile_url("twitter.com/AlexStone/?utm_campaign=x") == "https://x.com/AlexStone"
