from __future__ import annotations

import re
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from .contact_info import ContactInfo, extract_contact_info
from .credentials import (
    extract_authority_mentions,
    extract_credentials,
    extract_professional_titles,
)
from .handles import extract_handles, platform_for_url, username_from_profile
from .parser import parse_page
from .social_urls import extract_social_urls, profile_urls

NAME_PATTERN = re.compile(r"\b(?:Dr\.?\s+|Professor\s+)?[A-Z][A-Za-z’’-]{1,30}(?:\s+[A-Z][A-Za-z’’-]{1,30}){1,3}(?:\s+(?:MD|PhD))?\b")
NAME_STOPWORDS = {"Top Fitness", "Top Nutrition", "Instagram TikTok", "YouTube Facebook", "Certified Nutritionist"}

# Common words that appear in UI chrome, nav bars, legal footers, and site
# boilerplate. A "name" whose tokens are mostly these is not a real person.
_UI_TOKENS: frozenset[str] = frozenset({
    "reddit", "home", "sign", "log", "menu", "navigation", "open", "close",
    "skip", "explore", "popular", "news", "sort", "best", "new", "old",
    "controversial", "comments", "section", "privacy", "policy", "agreement",
    "portuguese", "german", "french", "spanish", "accessibility", "choices",
    "announcement", "moderator", "promoted", "email", "phone", "continue",
    "public", "anyone", "view", "post", "share", "people", "reply", "expand",
    "settings", "internet", "join", "please", "wait", "verification", "verified",
    "welcome", "accept", "cookies", "subscribe", "follow", "following",
    "trending", "search", "filter", "login", "signup", "register", "footer",
    "header", "sidebar", "advertisement", "sponsored", "promoted",
})
_GENERIC_TITLES: frozenset[str] = frozenset({"creator", "author", "speaker", "public figure"})


def _is_ui_text(name: str) -> bool:
    """Return True when the name looks like navigation or boilerplate rather than a person."""
    tokens = name.casefold().split()
    if not tokens:
        return True
    ui_overlap = sum(1 for t in tokens if t in _UI_TOKENS)
    return ui_overlap / len(tokens) > 0.4


def normalize_name(name: str) -> str:
    value = re.sub(r"\b(?:dr|professor|md|phd)\b\.?", " ", name.casefold())
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _spacy_person_names(text: str) -> list[str]:
    try:
        import spacy  # type: ignore[import-not-found]
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
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


def _platforms_for_mention(
    *,
    context: str,
    handle: str,
    page_platforms: dict[str, str],
    total_names: int,
    source_url: str,
) -> dict[str, str]:
    context_platforms = extract_social_urls(context, [], source_url)
    if context_platforms:
        return context_platforms

    if handle:
        handle_name = handle.removeprefix("@").casefold()
        matched = {
            platform: url
            for platform, url in page_platforms.items()
            if username_from_profile(url) == handle_name
        }
        if matched:
            return matched

    # Only trust page-level social links when the page appears to describe
    # a single creator; directory pages often expose unrelated navigation links.
    if total_names == 1:
        return dict(page_platforms)

    return {}


def extract_influencer_mentions(page: dict) -> list[dict[str, Any]]:
    text, links = parse_page(page)
    source_url = str(page.get("url") or page.get("source_url") or "")
    platforms = extract_social_urls(text, links, source_url)
    all_handles = extract_handles(text)

    raw_names = list(dict.fromkeys([*_spacy_person_names(text), *_deterministic_person_names(text)]))
    # Drop UI/boilerplate fragments before doing anything else
    names = [n for n in raw_names if not _is_ui_text(n)]

    if not names and all_handles:
        names = [all_handles[0]]
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
    for name in names[:25]:
        context = _context_for(text, name)

        # Find a handle that actually appears near this name in the text,
        # not by position in the global handle list.
        context_handles = extract_handles(context)
        handle = context_handles[0] if context_handles else ""

        credentials = extract_credentials(context)
        titles = extract_professional_titles(context)
        authority = extract_authority_mentions(context)
        mention_platforms = _platforms_for_mention(
            context=context,
            handle=handle,
            page_platforms=platforms,
            total_names=len(names),
            source_url=source_url,
        )
        strong_titles = [title for title in titles if title not in _GENERIC_TITLES]

        # Minimum signal gate: skip mentions with no handle, no credentials,
        # and no professional title — they are likely boilerplate noise.
        if not handle and not mention_platforms and not credentials and not strong_titles:
            continue

        mention_platform = platform_for_url(next(iter(mention_platforms.values()), "")) or ("instagram" if handle else "unknown")

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
            "profile_url": next(iter(mention_platforms.values()), None),
            "platforms": dict(mention_platforms) if mention_platforms else ({mention_platform: handle} if handle else {}),
            "profile_urls": profile_urls(mention_platforms), "credentials": credentials,
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
