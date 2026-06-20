"""Pipeline 19 - Event helpers.

Role 5 never writes to Redis directly. The Celery adapters call
:func:`emit_event` from :mod:`backend.core.cache.event_log` which the
broader platform wires to Redis. The helpers in this module construct
the **payload** for each role-5 event so the adapter layer can be a
single-line shim. The payloads are intentionally
:func:`dataclasses.asdict`-friendly so they serialize to JSON cleanly.

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


@dataclass
class InfluencerFound:
    name: str
    platform: str
    source: str

    def to_payload(self) -> dict[str, Any]:
        return {"name": self.name, "platform": self.platform, "source": self.source}


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
            "event_type": "score.calculated",
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


__all__ = [
    "IdentityMerged",
    "InfluencerFound",
    "ScoreCalculated",
]
