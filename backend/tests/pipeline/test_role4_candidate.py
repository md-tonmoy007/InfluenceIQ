"""Tests that content extraction produces a role4_candidate payload."""

from __future__ import annotations

from backend.pipeline.content.content_extractor import extract_role4_content

SAMPLE_PAGE = {
    "url": "https://example.com/test-creator",
    "html": """
    <html><head><title>Dr. Jane Smith</title>
    <meta name='description' content='Certified nutrition expert.'>
    </head><body>
    <h1>Jane Smith</h1>
    <p>@janesmith</p>
    <p>Certified Nutritionist, PhD in Health Sciences. 50K followers.</p>
    <p>Comments: Very informative and well-researched content.</p>
    <a href='https://instagram.com/janesmith'>Instagram</a>
    </body></html>
    """,
}


def test_extract_contains_role4_candidate() -> None:
    result = extract_role4_content(SAMPLE_PAGE)
    assert "role4_candidate" in result
    assert isinstance(result["role4_candidate"], dict)


def test_candidate_has_required_fields() -> None:
    candidate = extract_role4_content(SAMPLE_PAGE)["role4_candidate"]
    for key in ("source_url", "bio", "content", "comments", "data_source_count"):
        assert key in candidate
