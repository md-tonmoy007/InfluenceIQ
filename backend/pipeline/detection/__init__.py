"""Pipeline 3 - Fake / Suspicious Detection.

Role 5 detection happens **before** final scoring. The classifiers in this
package wrap the deterministic ``backend.pipeline.analysis`` scorers so the
Role 5 pipeline has a single import surface for the detection stage and
the category classifier can apply the spec's risk-band rules.

Detection categories:

* ``SAFE``
* ``SUSPICIOUS``
* ``HIGH_RISK``
* ``BOT_LIKE``
* ``FAKE_FOLLOWER``
* ``FAKE_COMMENT``
* ``SPAM_RING``
* ``BRAND_RISK``
* ``NEEDS_HUMAN_REVIEW``

Every detector returns an evidence dict with the underlying signal
values, thresholded reasons, and the raw 0-100 risk score so the
:class:`DetectionClassifier` can both classify and surface reasons.
"""

from __future__ import annotations

from backend.pipeline.detection.bot_behavior_detector import detect_bot_behavior
from backend.pipeline.detection.brand_safety_detector import detect_brand_safety
from backend.pipeline.detection.coordinated_ring_detector import detect_coordinated_engagement
from backend.pipeline.detection.detection_classifier import (
    DetectionCategory,
    DetectionDecision,
    classify_detection,
)
from backend.pipeline.detection.fake_comment_detector import detect_fake_comments
from backend.pipeline.detection.fake_follower_detector import detect_fake_followers

__all__ = [
    "DetectionCategory",
    "DetectionDecision",
    "classify_detection",
    "detect_brand_safety",
    "detect_bot_behavior",
    "detect_coordinated_engagement",
    "detect_fake_comments",
    "detect_fake_followers",
]
