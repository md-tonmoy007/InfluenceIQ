from __future__ import annotations

import re
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from .contact_info import ContactInfo, extract_contact_info
from .credentials import extract_authority_mentions, extract_credentials, extract_professional_titles
from .handles import extract_handles, platform_for_url, username_from_profile
from .parser import parse_page
from .social_urls import extract_social_urls, profile_urls

NAME_PATTERN = re.compile(r"\b(?:Dr\.?\s+|Professor\s+)?[A-Z][A-Za-z'’-]{1,30}(?:\s+[A-Z][A-Za-z'’-]{1,30}){1,3}(?:\s+(?:MD|PhD))?\b")
NAME_STOPWORDS = {"Top Fitness", "Top Nutrition", "Instagram TikTok", "YouTube Facebook", "Certified Nutritionist"}


def normalize_name(name: str) -> str:
    value = re.sub(r"\b(?:dr|professor|md|phd)\b\.?", " ", name.casefold())
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _spacy_person_names(text: str) -> list[str]:
    try:
        import spacy  # type: ignore[import-not-found]
        try:
            nlp = spacy.load("en_core_web_sm")
        except (OSError, IOError):
            return []
        return [entity.text.strip() for entity in nlp(text[:100_000]).ents if entity.label_ == "PERSON"]
    except ImportError:
        return []


def _deterministic_person_names(text: str) -> list[str]:
    names: list[str] = []
    for match in NAME_PATTERN.finditer(text):
        name = match.group(0).strip(" ,.;:-")
        if name not in NAME_STOPWORDS and not any(token.casefold() in {"instagram", "youtube", "facebook", "tiktok"} for token in name.split()):
            names.append(name)
    return names


def _context_for(text: str, token: str, radius: int = 180) -> str:
    index = text.casefold().find(token.casefold())
    if index < 0:
        return text[: radius * 2].strip()
    start = max(0, text.rfind(".", 0, index) + 1, index - radius)
    end_pos = text.find(".", index + len(token))
    end = min(len(text), end_pos + 1 if end_pos >= 0 else index + len(token) + radius)
    return re.sub(r"\s+", " ", text[start:end]).strip()


def extract_influencer_mentions(page: dict) -> list[dict[str, Any]]:
    text, links = parse_page(page)
    source_url = str(page.get("url") or page.get("source_url") or "")
    platforms = extract_social_urls(text, links, source_url)
    names = list(dict.fromkeys([*_spacy_person_names(text), *_deterministic_person_names(text)]))
    handles = extract_handles(text)
    if not names and handles:
        names = [handles[0]]
    if not names and platforms:
        username = username_from_profile(next(iter(platforms.values())))
        names = [f"@{username}"] if username else []

    # Page-level contact info is extracted once. Per-mention contact
    # info is a subset filtered to the mention's context window.
    page_contact: ContactInfo = extract_contact_info(text)
    page_contact_dict = page_contact.to_dict() if page_contact.enabled else {
        "emails": [], "phones": [], "websites": [], "addresses": [], "enabled": False,
    }

    mentions: list[dict[str, Any]] = []
    for index, name in enumerate(names[:25]):
        context = _context_for(text, name)
        handle = handles[index] if index < len(handles) else ""
        mention_platform = platform_for_url(next(iter(platforms.values()), "")) or ("instagram" if handle else "unknown")
        credentials = extract_credentials(context)
        titles = extract_professional_titles(context)
        authority = extract_authority_mentions(context)
        # Per-mention contact info is the intersection of the page's
        # contact lists with the mention's context window. When the
        # extractor is disabled every list is empty.
        context_lower = context.casefold()
        contact = extract_contact_info(context) if page_contact.enabled else page_contact
        contact_dict = {
            "emails": [e for e in contact.emails if e in context_lower or e in context.casefold()],
            "phones": [p for p in contact.phones if p in context],
            "websites": [w for w in contact.websites if w in context],
            "addresses": [a for a in contact.addresses if a.casefold() in context_lower or a in context],
            "enabled": contact.enabled,
        } if page_contact.enabled else page_contact_dict
        # Fall back to page-level contact for mentions with no contact
        # in their own context window but the page has some.
        if page_contact.enabled and not any(contact_dict[k] for k in ("emails", "phones", "websites", "addresses")):
            contact_dict = {
                "emails": list(page_contact.emails),
                "phones": list(page_contact.phones),
                "websites": list(page_contact.websites),
                "addresses": list(page_contact.addresses),
                "enabled": True,
            }
        evidence_count = sum(bool(value) for value in (name, handle, platforms, credentials, titles))
        contact_evidence = sum(bool(contact_dict[k]) for k in ("emails", "phones", "websites", "addresses"))
        mentions.append({
            "mention_id": str(uuid5(NAMESPACE_URL, f"{source_url}|{name}|{handle}")),
            "name": name, "handle": handle or None, "platform": mention_platform,
            "profile_url": next(iter(platforms.values()), None),
            "platforms": dict(platforms) if platforms else ({mention_platform: handle} if handle else {}),
            "profile_urls": profile_urls(platforms), "credentials": credentials,
            "professional_titles": titles, "authority_mentions": authority,
            "emails": contact_dict["emails"],
            "phones": contact_dict["phones"],
            "websites": contact_dict["websites"],
            "addresses": contact_dict["addresses"],
            "contact_info_enabled": contact_dict["enabled"],
            "source_url": source_url, "context": context,
            "extraction_confidence": round(
                min(0.98, 0.45 + 0.1 * evidence_count + 0.05 * contact_evidence),
                2,
            ),
        })
    return mentions
