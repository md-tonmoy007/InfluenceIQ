from pathlib import Path

from backend.pipeline.extraction.credentials import extract_credentials
from backend.pipeline.extraction.entities import extract_influencer_mentions
from backend.pipeline.extraction.handles import extract_handles, normalize_profile_url, is_profile_url, canonical_profile_url
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


def test_is_profile_url_tiktok() -> None:
    assert is_profile_url("https://www.tiktok.com/@being_lloyds") is True
    assert is_profile_url("https://www.tiktok.com/@being_lloyds/video/12345") is False
    assert is_profile_url("https://tiktok.com/@user.name") is True


def test_is_profile_url_youtube() -> None:
    assert is_profile_url("https://www.youtube.com/@Flickverseyt") is True
    assert is_profile_url("https://www.youtube.com/channel/UC1234567890") is True
    assert is_profile_url("https://www.youtube.com/c/LinusTechTips") is True
    assert is_profile_url("https://www.youtube.com/user/PewDiePie") is True
    assert is_profile_url("https://www.youtube.com/playlist?list=PL123") is False
    assert is_profile_url("https://www.youtube.com/watch?v=abc123") is False
    assert is_profile_url("https://www.youtube.com/shorts/abc123") is False
    assert is_profile_url("https://youtu.be/abc123") is False


def test_is_profile_url_unstructured_platforms() -> None:
    assert is_profile_url("https://www.instagram.com/someuser/") is True
    assert is_profile_url("https://www.instagram.com/p/abc123/") is True
    assert is_profile_url("https://x.com/someuser") is True
    assert is_profile_url("https://example.com/someuser") is False


def test_canonical_profile_url() -> None:
    assert canonical_profile_url("https://tiktok.com/@being_lloyds?lang=en") == "https://www.tiktok.com/@being_lloyds"
    assert canonical_profile_url("https://m.youtube.com/@Flickverseyt") == "https://www.youtube.com/@Flickverseyt"
    assert canonical_profile_url("https://www.tiktok.com/@user/video/123") is None
    assert canonical_profile_url("https://www.youtube.com/watch?v=abc123") is None


def test_social_urls_filters_non_profiles() -> None:
    result = extract_social_urls(links=[
        "https://www.youtube.com/@Flickverseyt",
        "https://www.youtube.com/playlist?list=PL123",
        "https://www.tiktok.com/@being_lloyds/video/12345",
    ])
    assert list(result.keys()) == ["youtube"]
    assert result["youtube"] == "https://www.youtube.com/@Flickverseyt"
