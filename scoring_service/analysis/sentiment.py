from __future__ import annotations

import re
from typing import Any

from scoring_service.model_classifiers import classify_with_model

POSITIVE_WORDS = {"accurate", "amazing", "authentic", "clear", "credible", "excellent", "helpful", "honest", "informative", "inspiring", "love", "professional", "recommend", "trusted", "useful"}
NEGATIVE_WORDS = {"awful", "bad", "boring", "dangerous", "dishonest", "fake", "fraud", "hate", "misleading", "poor", "scam", "spam", "terrible", "toxic", "unfollow", "wrong"}
NEGATIONS = {"not", "never", "no", "hardly"}
TOKEN_PATTERN = re.compile(r"[a-z']+")


def score_text(text: str) -> float:
    tokens = TOKEN_PATTERN.findall(text.casefold())
    total = matches = 0
    for index, token in enumerate(tokens):
        value = 1 if token in POSITIVE_WORDS else -1 if token in NEGATIVE_WORDS else 0
        if value:
            if any(word in NEGATIONS for word in tokens[max(0, index - 3):index]): value *= -1
            total += value
            matches += 1
    return round(max(-1.0, min(1.0, total / matches)), 4) if matches else 0.0


def sentiment_label(score: float) -> str:
    if score <= 30: return "negative"
    if score <= 60: return "mixed"
    if score <= 85: return "positive"
    return "strongly_positive"


def analyze_sentiment(comments: list[Any] | None, overall_fake_risk_score: float = 0.0) -> dict[str, Any]:
    texts = [str(item.get("text", "") if isinstance(item, dict) else item).strip() for item in comments or []]
    texts = [text for text in texts if text]
    values = [score_text(text) for text in texts]
    compound = round(sum(values) / len(values), 4) if values else 0.0
    heuristic_raw = round((compound + 1.0) * 50.0, 2)
    model_result = classify_with_model("sentiment_quality", {"comments": texts, "heuristic_score": heuristic_raw})
    raw = round(model_result.score, 2) if model_result is not None else heuristic_raw
    compound = round((raw / 50.0) - 1.0, 4)
    fake_risk = max(0.0, min(100.0, float(overall_fake_risk_score or 0)))
    adjusted = round(raw * (1 - 0.50 * fake_risk / 100), 2)
    reasons = ([f"Sentiment reduced by {raw - adjusted:.2f} points due to fake-engagement risk"] if raw > adjusted else [])
    if model_result is not None:
        reasons.extend(model_result.reasons)
    return {"compound": compound, "raw_sentiment_score": raw, "sentiment_score": adjusted,
            "heuristic_raw_sentiment_score": heuristic_raw,
            "model_sentiment_quality_probability": round(model_result.risk_probability, 4) if model_result is not None else None,
            "model_provider": model_result.provider if model_result is not None else None,
            "model_name": model_result.model if model_result is not None else None,
            "label": sentiment_label(adjusted), "sample_size": len(texts),
            "fake_risk_adjustment": round(raw - adjusted, 2),
            "reasons": list(dict.fromkeys(reasons)),
            "evidence": model_result.to_evidence() if model_result is not None else {}}
