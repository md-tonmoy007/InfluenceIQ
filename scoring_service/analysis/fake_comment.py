from __future__ import annotations

import re
from collections import Counter
from typing import Any

from scoring_service.model_classifiers import classify_with_model

GENERIC = {"nice", "amazing", "great post", "wow", "awesome", "follow back", "dm me", "check inbox", "buy now", "click link"}
SPAM_TERMS = {"follow back", "dm me", "check inbox", "buy now", "click link", "promo", "guaranteed profit"}
URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)


def _clamp(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _text(comment: Any) -> str:
    return str(comment.get("text", "") if isinstance(comment, dict) else comment).strip()


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def extract_comment_features(comments: list[Any] | None) -> dict[str, float]:
    texts = [_text(comment) for comment in comments or [] if _text(comment)]
    if not texts:
        return {name: 0.0 for name in ("generic_comment_ratio", "duplicate_comment_ratio", "emoji_only_ratio",
                "spam_keyword_ratio", "link_spam_ratio", "repeated_phrase_ratio", "low_context_comment_ratio")}
    normalized = [_normalized(text) for text in texts]
    counts = Counter(normalized)
    n = len(texts)
    generic = sum(value in GENERIC or any(value.startswith(term) for term in GENERIC) for value in normalized)
    duplicates = sum(count - 1 for count in counts.values() if count > 1)
    emoji_only = sum(not any(char.isalnum() for char in text) for text in texts)
    spam = sum(any(term in value for term in SPAM_TERMS) for value in normalized)
    links = sum(bool(URL_RE.search(text)) for text in texts)
    repeated_phrases = sum(count for phrase, count in counts.items() if phrase and count > 1)
    low_context = sum(len(value.split()) <= 2 for value in normalized)
    return {"generic_comment_ratio": generic / n, "duplicate_comment_ratio": duplicates / n,
            "emoji_only_ratio": emoji_only / n, "spam_keyword_ratio": spam / n, "link_spam_ratio": links / n,
            "repeated_phrase_ratio": repeated_phrases / n, "low_context_comment_ratio": low_context / n}


def score_fake_comments(features: dict[str, Any] | None = None, comments: list[Any] | None = None) -> dict[str, Any]:
    values = {**extract_comment_features(comments), **(features or {})}
    heuristic = 100 * _clamp(
        0.20 * _clamp(values.get("generic_comment_ratio")) + 0.20 * _clamp(values.get("duplicate_comment_ratio"))
        + 0.15 * _clamp(values.get("emoji_only_ratio")) + 0.15 * _clamp(values.get("spam_keyword_ratio"))
        + 0.10 * _clamp(values.get("link_spam_ratio")) + 0.10 * _clamp(values.get("low_context_comment_ratio"))
        + 0.10 * _clamp(values.get("aigc_probability")))
    model_result = None
    model_probability = values.get("model_fake_probability")
    if model_probability is None:
        model_result = classify_with_model("fake_comments", {"features": values, "comments": comments or []})
        if model_result is not None:
            model_probability = model_result.risk_probability
    score = 0.60 * _clamp(model_probability) * 100 + 0.40 * heuristic if model_probability is not None else heuristic
    reasons = []
    mapping = (("generic_comment_ratio", 0.35, "High generic comment ratio"),
               ("duplicate_comment_ratio", 0.20, "Repeated comments detected"),
               ("emoji_only_ratio", 0.30, "Emoji-only comments are unusually high"),
               ("spam_keyword_ratio", 0.15, "Spam keywords detected"),
               ("aigc_probability", 0.60, "Possible AI-generated comment pattern"))
    evidence = {}
    for key, threshold, reason in mapping:
        value = _clamp(values.get(key))
        if value >= threshold:
            reasons.append(reason)
            evidence[key] = round(value, 4)
    model_evidence = model_result.to_evidence() if model_result is not None else {}
    if model_result is not None:
        reasons.extend(model_result.reasons)
        evidence.update(model_evidence)
    return {"fake_comment_risk_score": round(score, 2), "heuristic_fake_comment_risk_score": round(heuristic, 2),
            "model_fake_probability": round(_clamp(model_probability), 4) if model_probability is not None else None,
            "model_provider": model_evidence.get("model_provider"),
            "model_name": model_evidence.get("model_name"),
            "features": {key: round(_clamp(value), 4) for key, value in values.items() if isinstance(value, (int, float))},
            "reasons": list(dict.fromkeys(reasons)), "evidence": evidence}
