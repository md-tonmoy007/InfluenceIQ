"""Pipeline 3 - Detection Category Classifier.

Applies the spec's risk-band rules to convert the four fake-risk scores
plus brand safety and data-source count into a single
``DetectionCategory``. The classifier is intentionally a pure function:
no I/O, no globals, and no LLM calls. The order of rules is important
because ``NEEDS_HUMAN_REVIEW`` is applied last, only when the stronger
signals have not already classified the record.

Rules (see ``Role-5-Scoring.md``):

* ``overall_fake_risk_score <= 20``              -> ``SAFE``
* ``21 <= overall_fake_risk_score <= 40``        -> ``SUSPICIOUS``
* ``41 <= overall_fake_risk_score <= 65``        -> ``HIGH_RISK``
* ``bot_behavior_risk_score > 70``               -> ``BOT_LIKE``
* ``fake_follower_risk_score > 70``              -> ``FAKE_FOLLOWER``
* ``fake_comment_risk_score > 70``               -> ``FAKE_COMMENT``
* ``coordinated_engagement_risk_score > 80``     -> ``SPAM_RING``
* ``brand_safety_score < 40``                    -> ``BRAND_RISK``
* ``data_source_count < 3 and overall_fake > 40`` -> ``NEEDS_HUMAN_REVIEW``
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class DetectionCategory(str, enum.Enum):
    """The 9 detection categories defined in the Role 5 spec."""

    SAFE = "SAFE"
    SUSPICIOUS = "SUSPICIOUS"
    HIGH_RISK = "HIGH_RISK"
    BOT_LIKE = "BOT_LIKE"
    FAKE_FOLLOWER = "FAKE_FOLLOWER"
    FAKE_COMMENT = "FAKE_COMMENT"
    SPAM_RING = "SPAM_RING"
    BRAND_RISK = "BRAND_RISK"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


@dataclass(frozen=True)
class DetectionDecision:
    """The full outcome of the detection classifier.

    Attributes
    ----------
    category:
        The :class:`DetectionCategory` value.
    risk_level:
        A coarse LOW / MEDIUM / HIGH / SEVERE label suitable for UI.
    is_fake_comment / is_fake_follower / is_bot_like / is_spam_ring:
        Per-detector boolean flags, useful for the dashboard.
    requires_human_review:
        True when the record needs manual review (severe brand-safety
        flag, sparse data + high fake risk, or LLM review required).
    matched_rules:
        List of human-readable rule descriptions that fired.
    """

    category: DetectionCategory
    risk_level: str
    is_fake_comment: bool
    is_fake_follower: bool
    is_bot_like: bool
    is_spam_ring: bool
    requires_human_review: bool
    matched_rules: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "detection_category": self.category.value,
            "risk_level": self.risk_level,
            "is_fake_comment": self.is_fake_comment,
            "is_fake_follower": self.is_fake_follower,
            "is_bot_like": self.is_bot_like,
            "is_spam_ring": self.is_spam_ring,
            "requires_human_review": self.requires_human_review,
            "matched_rules": list(self.matched_rules),
        }


def _coerce(value: Any, default: float = 0.0) -> float:
    """Coerce a numeric value to ``float`` with a default for ``None``."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _risk_level_for(category: DetectionCategory) -> str:
    if category in {DetectionCategory.SAFE}:
        return "LOW"
    if category in {DetectionCategory.SUSPICIOUS}:
        return "MEDIUM"
    if category in {DetectionCategory.HIGH_RISK}:
        return "HIGH"
    if category in {DetectionCategory.BOT_LIKE, DetectionCategory.FAKE_FOLLOWER,
                    DetectionCategory.FAKE_COMMENT, DetectionCategory.SPAM_RING,
                    DetectionCategory.BRAND_RISK, DetectionCategory.NEEDS_HUMAN_REVIEW}:
        return "SEVERE"
    return "LOW"


def classify_detection(
    *,
    overall_fake_risk_score: float | None = None,
    bot_behavior_risk_score: float | None = None,
    fake_follower_risk_score: float | None = None,
    fake_comment_risk_score: float | None = None,
    coordinated_engagement_risk_score: float | None = None,
    brand_safety_score: float | None = None,
    data_source_count: int | None = None,
    brand_safety_requires_llm: bool = False,
) -> DetectionDecision:
    """Classify a record using the spec's risk-band rules.

    Parameters
    ----------
    overall_fake_risk_score, bot_behavior_risk_score, fake_follower_risk_score,
    fake_comment_risk_score, coordinated_engagement_risk_score:
        Optional 0-100 risk scores. Missing values are treated as 0.
    brand_safety_score:
        0-100 brand-safety score (higher is safer). When ``None`` we
        skip the brand-risk rule.
    data_source_count:
        Number of independent sources. Defaults to 0.
    brand_safety_requires_llm:
        Forwarded from the brand-safety detector's LLM-review flag.

    Returns
    -------
    DetectionDecision
        Frozen dataclass exposing the category, coarse risk level, and
        per-detector boolean flags.
    """
    overall = _coerce(overall_fake_risk_score)
    bot = _coerce(bot_behavior_risk_score)
    follower = _coerce(fake_follower_risk_score)
    comment = _coerce(fake_comment_risk_score)
    coordinated = _coerce(coordinated_engagement_risk_score)
    safety = None if brand_safety_score is None else _coerce(brand_safety_score)
    sources = _coerce_int(data_source_count)

    matched: list[str] = []

    # Per-detector booleans are computed from the raw scores regardless of
    # which category wins - the dashboard wants to know whether each
    # detector flagged the record.
    is_fake_comment = comment > 70
    is_fake_follower = follower > 70
    is_bot_like = bot > 70
    is_spam_ring = coordinated > 80
    is_brand_risk = safety is not None and safety < 40

    if is_bot_like:
        matched.append("bot_behavior_risk_score > 70")
    if is_fake_follower:
        matched.append("fake_follower_risk_score > 70")
    if is_fake_comment:
        matched.append("fake_comment_risk_score > 70")
    if is_spam_ring:
        matched.append("coordinated_engagement_risk_score > 80")
    if is_brand_risk:
        matched.append("brand_safety_score < 40")

    # Apply the spec's risk-band rules in priority order. The per-detector
    # boolean flags are always set above regardless of which category wins
    # so downstream UI can show every fired detector. The category itself
    # uses the spec's listed rule order (bot -> follower -> comment ->
    # coordinated -> brand) before falling through to the overall-fake
    # risk bands.
    if is_bot_like:
        category = DetectionCategory.BOT_LIKE
    elif is_fake_follower:
        category = DetectionCategory.FAKE_FOLLOWER
    elif is_fake_comment:
        category = DetectionCategory.FAKE_COMMENT
    elif is_spam_ring:
        category = DetectionCategory.SPAM_RING
    elif is_brand_risk:
        category = DetectionCategory.BRAND_RISK
    elif overall > 65:
        category = DetectionCategory.HIGH_RISK
        matched.append("overall_fake_risk_score > 65")
    elif overall > 40:
        category = DetectionCategory.HIGH_RISK
        matched.append("41 <= overall_fake_risk_score <= 65")
    elif overall > 20:
        category = DetectionCategory.SUSPICIOUS
        matched.append("21 <= overall_fake_risk_score <= 40")
    else:
        category = DetectionCategory.SAFE
        matched.append("overall_fake_risk_score <= 20")

    requires_review = brand_safety_requires_llm
    if sources < 3 and overall > 40:
        requires_review = True
        category = DetectionCategory.NEEDS_HUMAN_REVIEW
        matched.append("data_source_count < 3 and overall_fake_risk_score > 40")
    elif is_brand_risk and sources < 3:
        requires_review = True

    return DetectionDecision(
        category=category,
        risk_level=_risk_level_for(category),
        is_fake_comment=is_fake_comment,
        is_fake_follower=is_fake_follower,
        is_bot_like=is_bot_like,
        is_spam_ring=is_spam_ring,
        requires_human_review=requires_review,
        matched_rules=matched,
    )


__all__ = ["DetectionCategory", "DetectionDecision", "classify_detection"]
