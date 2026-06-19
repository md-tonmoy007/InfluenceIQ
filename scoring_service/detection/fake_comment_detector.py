"""Pipeline 4 - Fake Comment Detection.

Wraps the deterministic scorer in :mod:`scoring_service.analysis.fake_comment`
and exposes a small, auditable detection result for the role-5 pipeline.

The underlying formula (see ``Role-5-Scoring.md``) is:

    fake_comment_risk_score = 100 * clamp(
        0.20 * generic_comment_ratio
      + 0.20 * duplicate_comment_ratio
      + 0.15 * emoji_only_ratio
      + 0.15 * spam_keyword_ratio
      + 0.10 * link_spam_ratio
      + 0.10 * low_context_comment_ratio
      + 0.10 * aigc_probability
    )

If ``model_fake_probability`` is supplied by an upstream classifier the
final score blends 60% model + 40% heuristic. The wrapper only formats
the evidence for the role-5 detection stage; the actual math lives in
``scoring_service.analysis.fake_comment``.
"""

from __future__ import annotations

from typing import Any

from scoring_service.analysis.fake_comment import score_fake_comments


def detect_fake_comments(features: dict[str, Any] | None = None,
                          comments: list[Any] | None = None) -> dict[str, Any]:
    """Run fake-comment detection and return an evidence-shaped result."""
    result = score_fake_comments(features=features, comments=comments)
    return {
        "detector": "fake_comment",
        "score": result["fake_comment_risk_score"],
        "heuristic_score": result["heuristic_fake_comment_risk_score"],
        "is_fake_comment": result["fake_comment_risk_score"] > 70,
        "reasons": list(result.get("reasons", [])),
        "evidence": result.get("features", {}),
        "trigger_evidence": result.get("evidence", {}),
    }
