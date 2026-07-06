"""Pipeline 19 - Event helpers.

Role 4 (and previously Role 5) never writes to Redis directly. The
Celery adapters call :func:`emit_event` from
:mod:`backend.core.cache.event_log` which the broader platform wires
to Redis. The helpers in this module construct the **payload** for
each role-4 event so the adapter layer can be a single-line shim.
The payloads are intentionally :func:`dataclasses.asdict`-friendly
so they serialize to JSON cleanly.

Contact information is **always redacted** in the public event
payload. The :class:`ScoreCalculated` event hashes emails, phones,
websites, and addresses via SHA-256 (truncated) before serializing.
The full plain-text values stay only in the canonical influencer
output that the backend stores in PostgreSQL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.pipeline.extraction.contact_info import (
    CONTACT_INFO_HASH_IN_EVENTS,
    redact_contact_info,
)
from backend.pipeline.fusion.versioning import computed_at

# ---------------------------------------------------------------------------
# Query & Search events
# ---------------------------------------------------------------------------


@dataclass
class QueryGenerationCompleted:
    campaign_id: str
    query_count: int
    queries: list[str]

    def to_payload(self) -> dict[str, Any]:
        return {
            "query_count": self.query_count,
            "queries": list(self.queries),
        }


@dataclass
class SearchExecuted:
    campaign_id: str
    query: str
    index: int
    result_count: int
    crawl_source_ids: list[str]

    def to_payload(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "index": self.index,
            "result_count": self.result_count,
            "crawl_source_ids": list(self.crawl_source_ids),
        }


@dataclass
class SearchFailed:
    campaign_id: str
    query: str
    index: int
    error: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "index": self.index,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Crawl / Fetch events
# ---------------------------------------------------------------------------


@dataclass
class PageFetched:
    campaign_id: str
    crawl_source_id: str
    url: str
    status: int
    cached: bool

    def to_payload(self) -> dict[str, Any]:
        return {
            "crawl_source_id": self.crawl_source_id,
            "url": self.url,
            "status": self.status,
            "cached": self.cached,
        }


@dataclass
class CrawlFailed:
    campaign_id: str
    crawl_source_id: str
    error: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "crawl_source_id": self.crawl_source_id,
            "error": self.error,
        }


@dataclass
class ContentExtracted:
    campaign_id: str
    crawl_source_id: str
    url: str | None
    title: str | None
    social_links: list[str]
    metrics: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        return {
            "crawl_source_id": self.crawl_source_id,
            "url": self.url,
            "title": self.title,
            "social_links": list(self.social_links),
            "metrics": dict(self.metrics),
        }


# ---------------------------------------------------------------------------
# Influencer events
# ---------------------------------------------------------------------------


@dataclass
class InfluencerFound:
    name: str
    platform: str
    source: str

    def to_payload(self) -> dict[str, Any]:
        return {"name": self.name, "platform": self.platform, "source": self.source}


@dataclass
class InfluencersNone:
    campaign_id: str
    crawl_source_id: str
    url: str | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "crawl_source_id": self.crawl_source_id,
            "url": self.url,
        }


# ---------------------------------------------------------------------------
# Identity events
# ---------------------------------------------------------------------------


@dataclass
class IdentityMerged:
    canonical_id: str
    merged_from: list[str]
    confidence: float

    def to_payload(self) -> dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "merged_from": list(self.merged_from),
            "confidence": round(float(self.confidence), 4),
        }


@dataclass
class IdentityResolved:
    campaign_id: str
    candidate_a: dict[str, Any]
    candidate_b: dict[str, Any]
    merge: bool
    confidence: float | None
    reason: str
    llm_used: bool
    llm_note: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "candidate_a": dict(self.candidate_a),
            "candidate_b": dict(self.candidate_b),
            "merge": self.merge,
            "confidence": round(float(self.confidence), 4) if self.confidence is not None else None,
            "reason": self.reason,
            "llm_used": self.llm_used,
            "llm_note": self.llm_note,
        }


@dataclass
class IdentityAmbiguous:
    campaign_id: str
    candidate_a: dict[str, Any]
    candidate_b: dict[str, Any]
    confidence: float
    reason: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "candidate_a": dict(self.candidate_a),
            "candidate_b": dict(self.candidate_b),
            "confidence": round(float(self.confidence), 4),
            "reason": self.reason,
        }


# ---------------------------------------------------------------------------
# Score event
# ---------------------------------------------------------------------------


@dataclass
class ScoreCalculated:
    """The ``score.calculated`` event payload used by the dashboard.

    ``contact_info`` (if supplied) is **always** passed through
    :func:`redact_contact_info` so the public event stream never
    carries raw PII. Set ``redact_contacts=False`` only on private
    internal events.
    """

    influencer_id: str
    overall_fake_risk: float
    detection_category: str
    risk_category: str
    final_score: float
    grade: str
    confidence: str
    contact_info: dict[str, Any] | None = None
    redact_contacts: bool = True
    computed_at: str = field(default_factory=computed_at)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "influencer_id": self.influencer_id,
            "overall_fake_risk": round(float(self.overall_fake_risk), 2),
            "detection_category": self.detection_category,
            "risk_category": self.risk_category,
            "final_score": round(float(self.final_score), 2),
            "grade": self.grade,
            "confidence": self.confidence,
            "computed_at": self.computed_at,
        }
        if self.contact_info:
            if self.redact_contacts and CONTACT_INFO_HASH_IN_EVENTS:
                payload["contact_info"] = redact_contact_info(self.contact_info)
            elif self.redact_contacts:
                payload["contact_info"] = redact_contact_info(self.contact_info, hash_in_events=False)
            else:
                payload["contact_info"] = dict(self.contact_info)
        return payload


# ---------------------------------------------------------------------------
# Brand-safety events
# ---------------------------------------------------------------------------


@dataclass
class BrandSafetyFlagged:
    campaign_id: str
    source_url: str
    mention_label: str
    influencer_id: str | None
    flag_count: int
    requires_llm_review: bool
    sample_flags: list[dict[str, Any]]

    def to_payload(self) -> dict[str, Any]:
        return {
            "source_url": self.source_url,
            "mention_label": self.mention_label,
            "influencer_id": self.influencer_id,
            "flag_count": self.flag_count,
            "requires_llm_review": self.requires_llm_review,
            "sample_flags": list(self.sample_flags),
        }


# ---------------------------------------------------------------------------
# Campaign lifecycle events
# ---------------------------------------------------------------------------


@dataclass
class CampaignCancelled:
    campaign_id: str
    reason: str
    influencer_count: int

    def to_payload(self) -> dict[str, Any]:
        return {
            "reason": self.reason,
            "influencer_count": self.influencer_count,
        }


# ---------------------------------------------------------------------------
# __all__
# ---------------------------------------------------------------------------


__all__ = [
    "BrandSafetyFlagged",
    "CampaignCancelled",
    "ContentExtracted",
    "CrawlFailed",
    "IdentityAmbiguous",
    "IdentityMerged",
    "IdentityResolved",
    "InfluencerFound",
    "InfluencersNone",
    "PageFetched",
    "QueryGenerationCompleted",
    "ScoreCalculated",
    "SearchExecuted",
    "SearchFailed",
]
