"""Tests that content extraction produces both role5_candidate and
role4_candidate keys during the transition period.
"""

from __future__ import annotations

import pytest

from backend.pipeline.content.content_extractor import extract_role5_content

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


def test_extract_contains_role5_key() -> None:
    """For backward compatibility, role5_candidate must be present."""
    result = extract_role5_content(SAMPLE_PAGE)
    assert "role5_candidate" in result
    assert isinstance(result["role5_candidate"], dict)


def test_extract_contains_role4_key() -> None:
    """The role4_candidate key must be present alongside role5_candidate."""
    result = extract_role5_content(SAMPLE_PAGE)
    assert "role4_candidate" in result
    assert isinstance(result["role4_candidate"], dict)


def test_both_keys_identical() -> None:
    """During the transition, both keys point to the same dict."""
    result = extract_role5_content(SAMPLE_PAGE)
    assert result["role5_candidate"] is result["role4_candidate"]


def test_candidate_has_required_fields() -> None:
    """The candidate dict has the fields scoring expects."""
    result = extract_role5_content(SAMPLE_PAGE)
    candidate = result["role4_candidate"]
    assert "source_url" in candidate
    assert "bio" in candidate
    assert "content" in candidate
    assert "comments" in candidate
    assert "data_source_count" in candidate
