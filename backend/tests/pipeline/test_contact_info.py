"""Tests for the role-5 contact-info extractor and event redaction."""

from __future__ import annotations

import re

from backend.pipeline.events import ScoreCalculated
from backend.pipeline.extraction import (
    ContactInfo,
    extract_addresses,
    extract_contact_info,
    extract_emails,
    extract_influencer_mentions,
    extract_phone_numbers,
    extract_websites,
    hash_contact,
    merge_contact_info,
    redact_contact_info,
)

# ---------------------------------------------------------------------------
# Email extraction
# ---------------------------------------------------------------------------

def test_extract_emails_basic() -> None:
    text = "Contact me at hello@drsarahtan.com or backup@brand.io"
    assert sorted(extract_emails(text)) == ["backup@brand.io", "hello@drsarahtan.com"]


def test_extract_emails_filters_placeholders() -> None:
    text = "ignore user@example.com and admin@test.com and root@localhost"
    assert extract_emails(text) == []


def test_extract_emails_dedupes_case_insensitively() -> None:
    text = "Sara@brand.com and sara@BRAND.com"
    result = extract_emails(text)
    assert result == ["sara@brand.com"]


def test_extract_emails_rejects_double_dots() -> None:
    text = "broken address: foo..bar@example.com"
    assert extract_emails(text) == []


def test_extract_emails_returns_empty_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("ROLE5_EXTRACT_CONTACT_INFO", "0")
    import importlib

    import backend.pipeline.extraction.contact_info as ci
    importlib.reload(ci)
    try:
        assert ci.extract_emails("contact me at hello@example.com") == []
        bundle = ci.extract_contact_info("hi sarahtan@gmail.com")
        assert not bundle.enabled
    finally:
        # restore the env-default enabled state for subsequent tests
        monkeypatch.delenv("ROLE5_EXTRACT_CONTACT_INFO", raising=False)
        importlib.reload(ci)


# ---------------------------------------------------------------------------
# Phone extraction
# ---------------------------------------------------------------------------

def test_extract_phone_numbers_international() -> None:
    text = "Call +1 415-555-0199 or (415) 555 0198 today."
    result = extract_phone_numbers(text)
    assert "+1 415-555-0199" in result
    assert "(415) 555 0198" in result


def test_extract_phone_numbers_rejects_short_or_long() -> None:
    text = "Phone: 12-34 or 99999999999999999999"
    result = extract_phone_numbers(text)
    # 12-34 has only 4 digits -> rejected. The 20-digit run is rejected.
    assert result == []


def test_extract_phone_numbers_rejects_year_only_match() -> None:
    # "in 2024 we..." should not produce a phone match for "2024"
    result = extract_phone_numbers("Founded in 2024 we have grown.")
    assert "2024" not in result


# ---------------------------------------------------------------------------
# Website extraction
# ---------------------------------------------------------------------------

def test_extract_websites_keeps_non_social_urls() -> None:
    text = "Visit https://drsarahtan.com and https://instagram.com/drsarahtan and https://mybrand.store"
    result = extract_websites(text)
    assert "https://drsarahtan.com" in result
    assert "https://mybrand.store" in result
    # The instagram URL must be filtered out
    assert not any("instagram.com" in url for url in result)


def test_extract_websites_filters_placeholder_domains() -> None:
    text = "Bad: https://example.com/page and https://www.example.org"
    assert extract_websites(text) == []


# ---------------------------------------------------------------------------
# Address extraction
# ---------------------------------------------------------------------------

def test_extract_addresses_street_with_city_state_zip() -> None:
    text = "Office at 123 Market Street, San Francisco, CA 94103 is open."
    result = extract_addresses(text)
    assert any("123 Market Street" in a and "San Francisco" in a for a in result)


def test_extract_addresses_po_box() -> None:
    text = "Mail to P.O. Box 1234 if you can't reach us."
    result = extract_addresses(text)
    assert any("P.O. Box 1234" in a for a in result)


def test_extract_addresses_po_box_no_periods() -> None:
    text = "Or PO Box 5678 please."
    result = extract_addresses(text)
    assert any("5678" in a for a in result)


def test_extract_addresses_skips_year_only_streets() -> None:
    # "1900 Avenue" must not match as a street address.
    text = "In 1900 Avenue was a long road."  # very weak fixture
    result = extract_addresses(text)
    # The regex should not match this in practice.
    assert all("1900" not in a for a in result)


# ---------------------------------------------------------------------------
# Bundling
# ---------------------------------------------------------------------------

def test_extract_contact_info_bundles_all() -> None:
    text = ("Email sarahtan@gmail.com Phone +1 415-555-0199 "
            "Web https://drsarahtan.com "
            "Address 123 Market Street, San Francisco, CA 94103")
    bundle = extract_contact_info(text)
    assert bundle.enabled
    assert "sarahtan@gmail.com" in bundle.emails
    assert any("415" in p for p in bundle.phones)
    assert "https://drsarahtan.com" in bundle.websites
    assert any("Market Street" in a for a in bundle.addresses)


def test_contact_info_to_dict_roundtrip() -> None:
    bundle = ContactInfo(emails=["a@b.com"], phones=["+1 415-555-0199"],
                          websites=["https://x.com"], addresses=["1 Main St"],
                          enabled=True)
    data = bundle.to_dict()
    assert data == {
        "emails": ["a@b.com"],
        "phones": ["+1 415-555-0199"],
        "websites": ["https://x.com"],
        "addresses": ["1 Main St"],
        "enabled": True,
    }


def test_merge_contact_info_unions_dedup() -> None:
    a = ContactInfo(emails=["a@b.com"], phones=["+1 415-555-0199"])
    b = ContactInfo(emails=["a@b.com", "c@d.com"], websites=["https://x.com"])
    merged = merge_contact_info([a, b])
    assert sorted(merged.emails) == ["a@b.com", "c@d.com"]
    assert merged.phones == ["+1 415-555-0199"]
    assert merged.websites == ["https://x.com"]


# ---------------------------------------------------------------------------
# Redaction + hashing
# ---------------------------------------------------------------------------

def test_hash_contact_is_stable_and_short() -> None:
    h = hash_contact("sarahtan@gmail.com")
    assert len(h) == 16
    assert re.match(r"^[0-9a-f]{16}$", h)
    assert h == hash_contact("sarahtan@gmail.com")
    assert h != hash_contact("SARAHTAN@gmail.com")  # case-sensitive hash


def test_redact_contact_info_hashes_when_enabled() -> None:
    info = ContactInfo(emails=["sarahtan@gmail.com"], phones=["+1 415-555-0199"])
    redacted = redact_contact_info(info, hash_in_events=True)
    assert redacted["emails"] == [hash_contact("sarahtan@gmail.com")]
    assert redacted["redacted"] is True


def test_redact_contact_info_empties_when_disabled() -> None:
    info = ContactInfo(emails=["sarahtan@gmail.com"])
    redacted = redact_contact_info(info, hash_in_events=False)
    assert redacted["emails"] == []
    assert redacted["phones"] == []
    assert redacted["redacted"] is True


def test_redact_contact_info_accepts_dict_input() -> None:
    redacted = redact_contact_info({
        "emails": ["x@y.com"], "phones": [], "websites": [], "addresses": [],
        "enabled": True,
    })
    assert redacted["emails"] == [hash_contact("x@y.com")]


def test_redact_contact_info_handles_none() -> None:
    redacted = redact_contact_info(None)
    assert redacted["emails"] == []
    assert redacted["redacted"] is True


# ---------------------------------------------------------------------------
# End-to-end: mention record
# ---------------------------------------------------------------------------

def test_mention_record_includes_contact_info() -> None:
    page = {
        "url": "https://source.test/profile.html",
        "html": ("<h1>Dr Sarah Tan MD</h1>"
                 "<p>Email sarahtan@gmail.com Phone +1 415-555-0199 "
                 "Web https://drsarahtan.com "
                 "Address 123 Market Street, San Francisco, CA 94103</p>"),
    }
    mentions = extract_influencer_mentions(page)
    assert mentions, "expected at least one mention"
    m = mentions[0]
    assert m.get("emails") == ["sarahtan@gmail.com"]
    assert any("415" in p for p in m.get("phones", []))
    assert "https://drsarahtan.com" in m.get("websites", [])
    assert any("Market Street" in a for a in m.get("addresses", []))
    # Confidence is bumped slightly when contact info is present
    assert m["extraction_confidence"] > 0.45


def test_mention_record_filters_placeholder_emails() -> None:
    page = {
        "url": "https://source.test/x",
        "html": ("<h1>Dr Sarah Tan</h1>"
                 "<p>Email ignore@example.com and contact@sarahtan.com</p>"),
    }
    mentions = extract_influencer_mentions(page)
    m = mentions[0]
    assert "contact@sarahtan.com" in m.get("emails", [])
    assert not any("example.com" in e for e in m.get("emails", []))


# ---------------------------------------------------------------------------
# End-to-end: pipeline + event redaction
# ---------------------------------------------------------------------------

def test_pipeline_event_redacts_contact_info_by_default() -> None:
    candidate = {
        "influencer_id": "i-1",
        "name": "Dr Sarah Tan",
        "data_source_count": 4,
        "comments": ["Helpful and authentic"],
        "mentions": [{
            "name": "Dr Sarah Tan",
            "source_url": "https://source.test/x",
            "emails": ["sarahtan@gmail.com"],
            "phones": ["+1 415-555-0199"],
            "websites": ["https://drsarahtan.com"],
            "addresses": ["123 Market Street, San Francisco, CA 94103"],
        }],
    }
    from backend.pipeline.orchestrator import run_role5_pipeline
    result = run_role5_pipeline(candidate).to_dict()

    # Backend contact_info is plain-text
    assert result["contact_info"]["emails"] == ["sarahtan@gmail.com"]
    # Public event contact_info is hashed
    event = result["score_event"]
    assert event["contact_info"]["redacted"] is True
    for field in ("emails", "phones", "websites", "addresses"):
        for value in event["contact_info"][field]:
            assert re.match(r"^[0-9a-f]{16}$", value), (field, value)


def test_pipeline_event_omits_contact_info_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("ROLE5_EXTRACT_CONTACT_INFO", "0")
    import importlib

    import backend.pipeline.extraction.contact_info as ci
    importlib.reload(ci)
    import backend.pipeline.extraction as ext
    importlib.reload(ext)
    import backend.pipeline.extraction.entities as ent
    importlib.reload(ent)
    import backend.pipeline.orchestrator.pipeline as orch
    importlib.reload(orch)
    import backend.pipeline.orchestrator as pipe
    importlib.reload(pipe)
    try:
        candidate = {
            "influencer_id": "i-1",
            "name": "Dr Sarah Tan",
            "data_source_count": 4,
            "mentions": [{
                "name": "Dr Sarah Tan",
                "source_url": "https://source.test/x",
                "emails": ["sarahtan@gmail.com"],
            }],
        }
        from backend.pipeline.orchestrator import run_role5_pipeline
        result = run_role5_pipeline(candidate).to_dict()
        assert result["contact_info"]["enabled"] is False
        # When extraction is disabled the event payload has no contact_info
        assert "contact_info" not in result["score_event"]
    finally:
        monkeypatch.delenv("ROLE5_EXTRACT_CONTACT_INFO", raising=False)
        importlib.reload(ci)
        importlib.reload(ext)
        importlib.reload(ent)
        importlib.reload(orch)
        importlib.reload(pipe)


def test_score_calculated_event_with_explicit_contact() -> None:
    event = ScoreCalculated(
        influencer_id="i-1",
        overall_fake_risk=10.0,
        detection_category="SAFE",
        risk_category="safe",
        final_score=80.0,
        grade="A",
        confidence="High",
        contact_info={"emails": ["sarahtan@gmail.com"], "phones": [], "websites": [], "addresses": [], "enabled": True},
    ).to_payload()
    assert event["contact_info"]["emails"] == [hash_contact("sarahtan@gmail.com")]
    assert event["contact_info"]["redacted"] is True


def test_score_calculated_event_without_contact() -> None:
    event = ScoreCalculated(
        influencer_id="i-1",
        overall_fake_risk=10.0,
        detection_category="SAFE",
        risk_category="safe",
        final_score=80.0,
        grade="A",
        confidence="High",
    ).to_payload()
    assert "contact_info" not in event
