"""Contact-info extraction (PII) for role-5 mentions.

This module extracts **contact information** found in the same context
window as an influencer mention:

* **Email addresses**       - ``local@domain.tld`` with placeholder
                              domains blocked
* **Phone numbers**         - permissive international regex, length
                              filtered, deduplicated
* **Generic website URLs**  - any URL whose host is not on the social
                              platform allowlist
* **Postal / physical addresses** - spaCy ``GPE / LOC / FAC`` entities
                                    (when ``en_core_web_sm`` is
                                    available), plus a deterministic
                                    street/PO-box regex fallback

The extractors are pure functions and never make network calls. They
are intentionally **not** wired into the fake-detection / trust
pipelines; PII has no role in scoring. They are exposed so the backend
can:

1. populate the mention record with the extracted contacts
2. redact them in the public ``score.calculated`` event payload
3. optionally hash them for cross-campaign linking

Enablement is controlled by :data:`CONTACT_INFO_ENABLED` (env var
``ROLE5_EXTRACT_CONTACT_INFO``). When disabled, the function returns
empty lists and a ``"disabled"`` flag, so the orchestrator never sees
null fields.
"""

from __future__ import annotations

import os
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Enable / disable
# ---------------------------------------------------------------------------

CONTACT_INFO_ENABLED: bool = os.environ.get("ROLE5_EXTRACT_CONTACT_INFO", "1").lower() in {
    "1", "true", "yes", "on",
}

# Hash contacts (SHA-256, truncated to 16 hex chars) when serializing
# into events so the public stream never carries raw PII.
CONTACT_INFO_HASH_IN_EVENTS: bool = os.environ.get("ROLE5_HASH_CONTACT_IN_EVENTS", "1").lower() in {
    "1", "true", "yes", "on",
}

# Placeholder / RFC-2606 / obviously-fake addresses and hosts are always
# rejected. This list is intentionally short - the regexes below also
# block common TLD patterns.
_BLOCKED_DOMAINS: frozenset[str] = frozenset({
    "example.com", "example.org", "example.net", "example.io",
    "test.com", "test.org", "test.io", "test.local",
    "localhost", "localhost.localdomain",
    "yourdomain.com", "mydomain.com", "company.com",
    "sentry.io", "wixpress.com", "wordpress.com", "cloudfront.net",
    "googleusercontent.com", "schema.org", "w3.org",
})

_PLATFORM_HOSTS: frozenset[str] = frozenset({
    "instagram.com", "x.com", "twitter.com", "tiktok.com",
    "youtube.com", "youtu.be", "facebook.com", "fb.com",
    "linkedin.com", "pinterest.com", "reddit.com", "threads.net",
    "snapchat.com", "twitch.tv", "t.me", "telegram.org",
})


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

# Conservative email regex. The negative-lookaheads reject common
# placeholder TLDs; ``_BLOCKED_DOMAINS`` is then applied to the
# captured local@domain to filter more specific cases.
EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@(?!example\.)(?!test\.)(?!localhost\b)(?!yourdomain\.)(?!mydomain\.)"
    r"[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
    flags=re.IGNORECASE,
)


def _is_valid_email(email: str) -> bool:
    local, _, domain = email.partition("@")
    if not local or not domain or ".." in local:
        return False
    domain = domain.casefold()
    if domain in _BLOCKED_DOMAINS:
        return False
    if any(domain.endswith(f".{blocked}") for blocked in _BLOCKED_DOMAINS):
        return False
    return True


def extract_emails(text: str) -> list[str]:
    """Return all unique, valid email addresses found in ``text``."""
    if not text or not CONTACT_INFO_ENABLED:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for match in EMAIL_RE.finditer(text):
        email = match.group(0).casefold()
        if not _is_valid_email(email):
            continue
        if email in seen:
            continue
        seen.add(email)
        found.append(email)
    return found


# ---------------------------------------------------------------------------
# Phone
# ---------------------------------------------------------------------------

# Permissive international phone regex. We accept 7-15 digits, optional
# country code, optional area code, common separators.
# libphonenumber would be more accurate but is an optional dependency.
PHONE_RE = re.compile(
    r"(?:\+\d{1,3}[\s\-]?)?"
    r"(?:\(\d{1,4}\)[\s\-]?)?"
    r"\d{2,4}[\s\-\.]?\d{2,4}[\s\-\.]?\d{2,4}"
    r"(?:[\s\-\.]?\d{1,5})?",
    flags=re.UNICODE,
)

# 4-digit runs inside a longer year-like context are common false
# positives. We skip matches that look like years (1900-2099) when
# they appear inside prose.
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def _is_valid_phone(candidate: str, text: str) -> bool:
    digits = re.sub(r"\D", "", candidate)
    if len(digits) < 7 or len(digits) > 15:
        return False
    # Reject if the digits are a 4-digit year embedded in a longer
    # non-phone sentence.
    if len(digits) == 4 and _YEAR_RE.fullmatch(digits):
        return False
    # Reject if the candidate is contained inside a date expression.
    if re.search(r"\d{1,2}[/\-]\d{1,2}[/\-]" + re.escape(candidate), text):
        return False
    return True


def extract_phone_numbers(text: str) -> list[str]:
    """Return all unique, plausible phone numbers found in ``text``."""
    if not text or not CONTACT_INFO_ENABLED:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for match in PHONE_RE.finditer(text):
        candidate = match.group(0).strip()
        if not _is_valid_phone(candidate, text):
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        found.append(candidate)
    return found


# ---------------------------------------------------------------------------
# Websites (non-social URLs)
# ---------------------------------------------------------------------------

GENERIC_URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"']+", re.IGNORECASE)


def _is_platform_or_blocked(url: str) -> bool:
    host = url.split("//", 1)[-1].split("/", 1)[0].casefold()
    host = host.removeprefix("www.").removeprefix("m.")
    if host in _PLATFORM_HOSTS:
        return True
    if host in _BLOCKED_DOMAINS:
        return True
    return False


def extract_websites(text: str) -> list[str]:
    """Return all unique non-social, non-placeholder website URLs."""
    if not text or not CONTACT_INFO_ENABLED:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for match in GENERIC_URL_RE.finditer(text or ""):
        url = match.group(0).rstrip(".,);]")
        if _is_platform_or_blocked(url):
            continue
        if url in seen:
            continue
        seen.add(url)
        found.append(url)
    return found


# ---------------------------------------------------------------------------
# Postal addresses
# ---------------------------------------------------------------------------

# Street address regex - matches common US/UK/EU patterns. This is a
# best-effort fallback; the spaCy GPE/LOC/FAC extractor is preferred.
STREET_RE = re.compile(
    r"\b\d{1,6}\s+[A-Z][A-Za-z'.\-]+(?:\s+[A-Z][A-Za-z'.\-]+){0,4}"
    r"(?:\s+(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Boulevard|Blvd\.?|"
    r"Lane|Ln\.?|Drive|Dr\.?|Court|Ct\.?|Way|Place|Pl\.?|Terrace|Ter\.?))\b"
    r"(?:[,\s]+(?:[A-Z][A-Za-z'.\-]+\s*)?\d{1,6}(?:-\d{1,5})?)?",
    flags=re.UNICODE,
)

# PO Box
POBOX_RE = re.compile(r"\bP\.?O\.?\s*Box\s+\d{1,8}\b", re.IGNORECASE)

# City / state / zip (US-ish). Used in conjunction with the street
# regex to assemble a full address.
CITY_STATE_ZIP_RE = re.compile(
    r"\b[A-Z][A-Za-z'.\-]+(?:\s+[A-Z][A-Za-z'.\-]+){0,2},?\s+"
    r"(?:[A-Z]{2}\s+)?\d{5}(?:-\d{4})?\b",
    flags=re.UNICODE,
)


def _spacy_locations(text: str) -> list[str]:
    """Extract GPE/LOC/FAC entities via spaCy when available."""
    try:
        import spacy  # type: ignore
    except ImportError:
        return []
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        return []
    return [
        entity.text.strip() for entity in nlp(text[:100_000]).ents
        if entity.label_ in {"GPE", "LOC", "FAC"}
    ]


def extract_addresses(text: str) -> list[str]:
    """Extract postal / physical addresses from ``text``.

    Strategy:

    1. spaCy ``GPE / LOC / FAC`` entities when available.
    2. Street + city/state/zip regex matches.
    3. PO Box matches.

    Results are deduplicated and returned in order of appearance.
    """
    if not text or not CONTACT_INFO_ENABLED:
        return []

    found: list[str] = []
    seen: set[str] = set()

    def _add(candidate: str) -> None:
        cleaned = re.sub(r"\s+", " ", candidate).strip(" ,.;:")
        if not cleaned or cleaned in seen:
            return
        seen.add(cleaned)
        found.append(cleaned)

    # 1. spaCy locations
    for entity in _spacy_locations(text):
        _add(entity)

    # 2. Street + city/state/zip
    for match in STREET_RE.finditer(text):
        street = match.group(0)
        # Look ahead for an attached city/state/zip within ~80 chars.
        end = match.end()
        tail = text[end:end + 80]
        city_match = CITY_STATE_ZIP_RE.search(tail)
        if city_match:
            _add(f"{street}, {city_match.group(0)}")
        else:
            _add(street)

    # 3. PO Box
    for match in POBOX_RE.finditer(text):
        _add(match.group(0))

    return found


# ---------------------------------------------------------------------------
# Bundle
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ContactInfo:
    """The combined result of :func:`extract_contact_info`."""

    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    websites: list[str] = field(default_factory=list)
    addresses: list[str] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> dict[str, list[str] | bool]:
        return {
            "emails": list(self.emails),
            "phones": list(self.phones),
            "websites": list(self.websites),
            "addresses": list(self.addresses),
            "enabled": self.enabled,
        }

    def is_empty(self) -> bool:
        return not (self.emails or self.phones or self.websites or self.addresses)


def extract_contact_info(text: str) -> ContactInfo:
    """Run all four extractors and return a :class:`ContactInfo` bundle."""
    if not CONTACT_INFO_ENABLED:
        return ContactInfo(enabled=False)
    return ContactInfo(
        emails=extract_emails(text),
        phones=extract_phone_numbers(text),
        websites=extract_websites(text),
        addresses=extract_addresses(text),
        enabled=True,
    )


# ---------------------------------------------------------------------------
# Hashing for event-payload redaction
# ---------------------------------------------------------------------------

import hashlib


def hash_contact(value: str, *, length: int = 16) -> str:
    """SHA-256 hash a contact value and return a ``length``-char prefix."""
    if not value:
        return ""
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return digest[:length]


def redact_contact_info(info: ContactInfo | dict[str, Any] | None,
                        *, hash_in_events: bool | None = None) -> dict[str, Any]:
    """Return a redacted view of contact info safe to put in events.

    When :data:`CONTACT_INFO_HASH_IN_EVENTS` is true (the default) the
    fields are replaced with their SHA-256 prefix and a ``redacted``
    flag. When false, the fields are emptied entirely so the event
    payload carries no contact trace.

    Accepts both :class:`ContactInfo` objects and plain dicts; uses
    duck-typing via a ``to_dict()`` method when present so the
    function is robust to module reloads.
    """
    if info is None:
        payload: dict[str, Any] = {"emails": [], "phones": [], "websites": [], "addresses": [], "enabled": False}
    else:
        to_dict = getattr(info, "to_dict", None)
        if callable(to_dict):
            payload = to_dict()
        elif isinstance(info, dict):
            payload = {
                "emails": list(info.get("emails", []) or []),
                "phones": list(info.get("phones", []) or []),
                "websites": list(info.get("websites", []) or []),
                "addresses": list(info.get("addresses", []) or []),
                "enabled": bool(info.get("enabled", True)),
            }
        else:
            payload = {"emails": [], "phones": [], "websites": [], "addresses": [], "enabled": False}

    do_hash = CONTACT_INFO_HASH_IN_EVENTS if hash_in_events is None else bool(hash_in_events)
    for key in ("emails", "phones", "websites", "addresses"):
        values = payload.get(key, []) or []
        if do_hash:
            payload[key] = [hash_contact(str(v)) for v in values]
        else:
            payload[key] = []
    payload["redacted"] = True
    return payload


def merge_contact_info(items: Iterable[ContactInfo | dict[str, Any] | None]) -> ContactInfo:
    """Union several :class:`ContactInfo` bundles into one, preserving order.

    Accepts both :class:`ContactInfo` objects and plain dicts. A
    duck-typed ``.to_dict()`` method is preferred; otherwise the item
    is treated as a dict directly. This avoids spurious
    ``isinstance`` failures when callers reload the module.
    """
    emails: list[str] = []
    phones: list[str] = []
    websites: list[str] = []
    addresses: list[str] = []
    enabled = False
    seen_e: set[str] = set()
    seen_p: set[str] = set()
    seen_w: set[str] = set()
    seen_a: set[str] = set()
    for item in items:
        if item is None:
            continue
        # Resolve a dict-like payload via duck-typing. This is robust
        # to module reloads and to classes that mimic the public API.
        to_dict = getattr(item, "to_dict", None)
        data = to_dict() if callable(to_dict) else item
        if not isinstance(data, dict):
            continue
        enabled = enabled or bool(data.get("enabled", True))
        for email in data.get("emails", []) or []:
            if email not in seen_e:
                seen_e.add(email)
                emails.append(email)
        for phone in data.get("phones", []) or []:
            if phone not in seen_p:
                seen_p.add(phone)
                phones.append(phone)
        for website in data.get("websites", []) or []:
            if website not in seen_w:
                seen_w.add(website)
                websites.append(website)
        for address in data.get("addresses", []) or []:
            if address not in seen_a:
                seen_a.add(address)
                addresses.append(address)
    return ContactInfo(emails=emails, phones=phones, websites=websites,
                       addresses=addresses, enabled=enabled)


# ---------------------------------------------------------------------------
# Optional: normalize via unicodedata to keep unicode emails valid
# ---------------------------------------------------------------------------


def _normalize_unicode(value: str) -> str:
    """Strip combining marks and zero-width chars (used internally)."""
    if not value:
        return ""
    stripped = "".join(ch for ch in unicodedata.normalize("NFKD", value)
                       if not unicodedata.combining(ch))
    return stripped.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")


__all__ = [
    "CONTACT_INFO_ENABLED",
    "CONTACT_INFO_HASH_IN_EVENTS",
    "ContactInfo",
    "extract_addresses",
    "extract_contact_info",
    "extract_emails",
    "extract_phone_numbers",
    "extract_websites",
    "hash_contact",
    "merge_contact_info",
    "redact_contact_info",
]
