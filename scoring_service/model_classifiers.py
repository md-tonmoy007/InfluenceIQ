"""Optional API-backed model classifiers for Role 5.

The rest of Role 5 remains deterministic by default. This module only
calls an external model when both conditions are true:

* ``ROLE5_USE_MODEL_CLASSIFIERS=1``
* ``OPENAI_API_KEY`` is set

Any error returns ``None`` so the existing heuristic score path remains
the production fallback.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-4o-mini"
MAX_TEXT_CHARS = 8_000


@dataclass(frozen=True)
class ModelClassification:
    task: str
    risk_probability: float
    score: float
    confidence: float
    categories: list[str]
    reasons: list[str]
    provider: str
    model: str

    def to_evidence(self) -> dict[str, Any]:
        return {
            "model_task": self.task,
            "model_risk_probability": round(self.risk_probability, 4),
            "model_score": round(self.score, 2),
            "model_confidence": round(self.confidence, 4),
            "model_categories": self.categories,
            "model_reasons": self.reasons,
            "model_provider": self.provider,
            "model_name": self.model,
        }


def model_classifiers_enabled() -> bool:
    return os.getenv("ROLE5_USE_MODEL_CLASSIFIERS", "").strip().lower() in {"1", "true", "yes", "on"}


def classify_with_model(task: str, payload: dict[str, Any]) -> ModelClassification | None:
    """Classify a Role-5 signal with the configured provider.

    Currently this uses OpenAI's Responses API with a strict JSON schema.
    The caller should treat ``None`` as "model unavailable" and continue
    with deterministic heuristics.
    """
    if not model_classifiers_enabled():
        return None
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("ROLE5_MODEL_CLASSIFIER_MODEL") or os.getenv("OPENAI_JUDGE_MODEL") or DEFAULT_MODEL
    request_payload = {
        "model": model,
        "input": [
            {"role": "system", "content": _system_prompt(task)},
            {"role": "user", "content": json.dumps(_safe_payload(task, payload), ensure_ascii=True, sort_keys=True)},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "role5_signal_classification",
                "strict": True,
                "schema": _response_schema(),
            }
        },
    }
    try:
        response = httpx.post(
            OPENAI_RESPONSES_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=request_payload,
            timeout=float(os.getenv("ROLE5_MODEL_CLASSIFIER_TIMEOUT", "8")),
        )
        response.raise_for_status()
        data = _extract_json(response.json())
        return _parse_result(task, data, model)
    except Exception:
        return None


def _system_prompt(task: str) -> str:
    task_prompt = {
        "fake_comments": "Estimate whether the comments look fake, spammy, low-context, duplicated, or artificially generated.",
        "bot_behavior": "Estimate whether the account activity pattern looks automated or bot-like.",
        "fake_followers": "Estimate whether the follower/audience pattern suggests suspicious or fake followers.",
        "brand_safety": "Estimate brand-safety risk. Flag risks such as scams, hate, harassment, misinformation, violence, adult content, dangerous products, or extremism.",
        "sentiment_quality": "Estimate audience sentiment quality. score must be the positive trust/sentiment quality from 0 to 100; risk_probability is the probability the sentiment is low-quality, manipulated, spammy, or unreliable.",
    }.get(task, "Classify this Role-5 signal.")
    return (
        "You are a conservative influencer trust-risk classifier. "
        "Use only the supplied evidence. Return calibrated probabilities, not accusations. "
        "Do not infer protected attributes or private facts. "
        f"Task: {task_prompt}"
    )


def _response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "risk_probability": {"type": "number", "minimum": 0, "maximum": 1},
            "score": {"type": "number", "minimum": 0, "maximum": 100},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "categories": {"type": "array", "items": {"type": "string"}},
            "reasons": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["risk_probability", "score", "confidence", "categories", "reasons"],
    }


def _safe_payload(task: str, payload: dict[str, Any]) -> dict[str, Any]:
    if task == "brand_safety":
        return {
            "text": _trim(payload.get("text", "")),
            "source_url": str(payload.get("source_url", ""))[:500],
            "heuristic_flags": payload.get("heuristic_flags", []),
            "heuristic_risks": payload.get("heuristic_risks", {}),
        }
    if task == "sentiment_quality":
        return {"comments": _safe_comments(payload.get("comments", [])), "heuristic_score": payload.get("heuristic_score")}
    if task == "fake_comments":
        return {"comments": _safe_comments(payload.get("comments", [])), "features": _numeric_features(payload.get("features", {}))}
    return {"features": _numeric_features(payload.get("features", payload))}


def _safe_comments(comments: Any) -> list[str]:
    values = []
    for item in list(comments or [])[:30]:
        text = str(item.get("text", "") if isinstance(item, dict) else item).strip()
        if text:
            values.append(_trim(text, 280))
    return values


def _numeric_features(features: Any) -> dict[str, float | str | bool]:
    if not isinstance(features, dict):
        return {}
    allowed: dict[str, float | str | bool] = {}
    for key, value in features.items():
        if key in {"emails", "phones", "addresses", "contact_info"}:
            continue
        if isinstance(value, bool):
            allowed[str(key)] = value
        elif isinstance(value, (int, float)):
            allowed[str(key)] = float(value)
        elif key in {"handle", "platform", "account_type"} and value is not None:
            allowed[str(key)] = str(value)[:120]
    return allowed


def _trim(value: Any, limit: int = MAX_TEXT_CHARS) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def _extract_json(response: dict[str, Any]) -> dict[str, Any]:
    if isinstance(response.get("output_text"), str):
        return json.loads(response["output_text"])
    for output in response.get("output", []) or []:
        for content in output.get("content", []) or []:
            if isinstance(content.get("text"), str):
                return json.loads(content["text"])
    raise ValueError("No JSON text found in model response")


def _parse_result(task: str, data: dict[str, Any], model: str) -> ModelClassification:
    return ModelClassification(
        task=task,
        risk_probability=_ratio(data.get("risk_probability")),
        score=_score(data.get("score")),
        confidence=_ratio(data.get("confidence")),
        categories=[str(item)[:80] for item in data.get("categories", []) if str(item).strip()],
        reasons=[str(item)[:240] for item in data.get("reasons", []) if str(item).strip()],
        provider="openai",
        model=model,
    )


def _ratio(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _score(value: Any) -> float:
    try:
        return max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


__all__ = ["ModelClassification", "classify_with_model", "model_classifiers_enabled"]
