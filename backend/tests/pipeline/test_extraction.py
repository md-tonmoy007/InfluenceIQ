from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://x:x@localhost:5432/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

from pathlib import Path

from backend.pipeline.extraction.credentials import extract_credentials
from backend.pipeline.extraction.entities import extract_influencer_mentions
from backend.pipeline.extraction.handles import (
    canonical_profile_url,
    extract_handles,
    is_profile_url,
    normalize_profile_url,
    platform_for_url,
)
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


def test_is_profile_url_instagram() -> None:
    assert is_profile_url("https://www.instagram.com/someuser/") is True
    assert is_profile_url("https://instagram.com/realusername") is True
    assert is_profile_url("https://www.instagram.com/user.name") is True
    assert is_profile_url("https://www.instagram.com/p/CxyzABC123/") is False
    assert is_profile_url("https://www.instagram.com/reel/CxyzABC123/") is False
    assert is_profile_url("https://www.instagram.com/reels/123/") is False
    assert is_profile_url("https://www.instagram.com/stories/realusername/123/") is False
    assert is_profile_url("https://www.instagram.com/explore/tags/fitness/") is False
    assert is_profile_url("https://www.instagram.com/tv/123/") is False
    assert is_profile_url("https://www.instagram.com/accounts/123/") is False
    assert is_profile_url("https://www.instagram.com/direct/123/") is False


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


def test_platform_for_url_trimmed_to_three() -> None:
    assert platform_for_url("https://youtube.com/@someone") == "youtube"
    assert platform_for_url("https://tiktok.com/@someone") == "tiktok"
    assert platform_for_url("https://instagram.com/someone") == "instagram"
    assert platform_for_url("https://x.com/someuser") is None
    assert platform_for_url("https://twitter.com/someuser") is None
    assert platform_for_url("https://facebook.com/someuser") is None
    assert platform_for_url("https://linkedin.com/in/someuser") is None


def test_social_urls_drops_non_three_platforms() -> None:
    result = extract_social_urls(links=[
        "https://www.instagram.com/realuser/",
        "https://www.instagram.com/reel/abc123/",
        "https://x.com/someuser",
    ])
    assert list(result.keys()) == ["instagram"]
    assert result["instagram"] == "https://instagram.com/realuser"


def test_normalize_llm_mentions_rejects_non_three_platform() -> None:
    from backend.pipeline.tasks.extract import _normalize_llm_mentions

    items = [{"platform": "linkedin", "handle": "someuser", "name": "Some User"}]
    mentions = _normalize_llm_mentions(items, "https://example.com/page")
    assert len(mentions) == 1
    assert mentions[0]["platforms"] == {}
    assert mentions[0]["profile_url"] is None


def test_normalize_llm_mentions_rejects_reserved_instagram_path() -> None:
    from backend.pipeline.tasks.extract import _normalize_llm_mentions

    items = [{"platform": "instagram", "handle": "explore", "name": "explore"}]
    mentions = _normalize_llm_mentions(items, "https://example.com/page")
    assert len(mentions) == 1
    assert mentions[0]["platforms"] == {}
    assert mentions[0]["profile_url"] is None


def test_verify_profile_mentions_llm_flag_off_returns_unchanged() -> None:
    from unittest.mock import patch

    from backend.pipeline.tasks.extract import _verify_profile_mentions_llm

    mentions = [{
        "name": "test",
        "platforms": {"instagram": "https://instagram.com/testuser"},
        "profile_urls": ["https://instagram.com/testuser"],
        "profile_url": "https://instagram.com/testuser",
    }]
    with patch.dict("os.environ", {"AI_AGENT_LLM_PROFILE_VERIFY": "0"}):
        result = _verify_profile_mentions_llm(mentions, {"url": "https://example.com", "content": "test"})
    assert result == mentions


def test_verify_profile_mentions_llm_flag_on_no_backend_returns_unchanged() -> None:
    from unittest.mock import patch

    from backend.pipeline.tasks.extract import _verify_profile_mentions_llm

    mentions = [{
        "name": "test",
        "platforms": {"instagram": "https://instagram.com/testuser"},
        "profile_urls": ["https://instagram.com/testuser"],
        "profile_url": "https://instagram.com/testuser",
    }]
    with patch.dict("os.environ", {"AI_AGENT_LLM_PROFILE_VERIFY": "1"}), \
         patch("backend.ml.models.registry.registry") as mock_registry:
        mock_registry.return_value.get.return_value = None
        result = _verify_profile_mentions_llm(mentions, {"url": "https://example.com", "content": "test"})
    assert result == mentions


def test_verify_profile_mentions_llm_flag_on_error_returns_unchanged() -> None:
    from unittest.mock import MagicMock, patch

    from backend.pipeline.tasks.extract import _verify_profile_mentions_llm

    mentions = [{
        "name": "test",
        "platforms": {"instagram": "https://instagram.com/testuser"},
        "profile_urls": ["https://instagram.com/testuser"],
        "profile_url": "https://instagram.com/testuser",
    }]
    mock_backend = MagicMock()
    mock_backend.predict_text.side_effect = RuntimeError("boom")
    with patch.dict("os.environ", {"AI_AGENT_LLM_PROFILE_VERIFY": "1"}), \
         patch("backend.ml.models.registry.registry") as mock_registry:
        mock_registry.return_value.get.return_value = mock_backend
        result = _verify_profile_mentions_llm(mentions, {"url": "https://example.com", "content": "test"})
    assert result == mentions


def test_verify_profile_mentions_llm_flag_on_verifies_subset() -> None:
    import json
    from unittest.mock import MagicMock, patch

    from backend.pipeline.tasks.extract import _verify_profile_mentions_llm

    mentions = [
        {
            "name": "alice",
            "platforms": {"instagram": "https://instagram.com/alice"},
            "profile_urls": ["https://instagram.com/alice"],
            "profile_url": "https://instagram.com/alice",
        },
        {
            "name": "bob",
            "platforms": {"instagram": "https://instagram.com/bob"},
            "profile_urls": ["https://instagram.com/bob"],
            "profile_url": "https://instagram.com/bob",
        },
    ]
    mock_backend = MagicMock()
    mock_backend.predict_text.return_value = json.dumps([0])
    with patch.dict("os.environ", {"AI_AGENT_LLM_PROFILE_VERIFY": "1"}), \
         patch("backend.ml.models.registry.registry") as mock_registry, \
         patch("backend.pipeline.tasks.search._run_predict", return_value=json.dumps([0])):
        mock_registry.return_value.get.return_value = mock_backend
        result = _verify_profile_mentions_llm(mentions, {"url": "https://example.com", "content": "test"})
    assert result[0]["platforms"] == {"instagram": "https://instagram.com/alice"}
    assert result[1]["platforms"] == {}


def test_verify_profile_mentions_llm_flag_on_verifies_none_strips_all() -> None:
    import json
    from unittest.mock import MagicMock, patch

    from backend.pipeline.tasks.extract import _verify_profile_mentions_llm

    mentions = [
        {
            "name": "alice",
            "platforms": {"instagram": "https://instagram.com/alice"},
            "profile_urls": ["https://instagram.com/alice"],
            "profile_url": "https://instagram.com/alice",
        },
    ]
    with patch.dict("os.environ", {"AI_AGENT_LLM_PROFILE_VERIFY": "1"}), \
         patch("backend.ml.models.registry.registry") as mock_registry, \
         patch("backend.pipeline.tasks.search._run_predict", return_value=json.dumps([])):
        mock_registry.return_value.get.return_value = MagicMock()
        result = _verify_profile_mentions_llm(mentions, {"url": "https://example.com", "content": "test"})
    assert result[0]["name"] == "alice"
    assert result[0]["platforms"] == {}
    assert result[0]["profile_url"] is None
