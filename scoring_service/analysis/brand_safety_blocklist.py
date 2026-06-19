from __future__ import annotations

import re
from typing import Any

from scoring_service.model_classifiers import classify_with_model

BLOCKLIST = {
    "hate_speech": [("hate speech", "high"), ("racial slur", "severe")],
    "scam": [("get rich quick", "high"), ("guaranteed profit", "high"), ("ponzi", "severe"), ("scam", "medium")],
    "fraud": [("identity fraud", "high"), ("forged documents", "high")],
    "adult_content": [("nsfw", "medium"), ("explicit content", "high")],
    "violence": [("graphic violence", "high"), ("death threat", "severe")],
    "political_extremism": [("terror propaganda", "severe"), ("violent extremism", "severe")],
    "harassment": [("doxxing", "severe"), ("harassment", "medium")],
    "misinformation": [("fake cure", "high"), ("miracle cure", "high"), ("misinformation", "medium"), ("hoax", "medium")],
    "dangerous_products": [("illegal steroids", "high"), ("unapproved drug", "high")],
    "controversial_claims": [("guaranteed cure", "high"), ("doctors are hiding", "medium")],
}
PENALTIES = {"minor": 15, "medium": 35, "high": 60, "severe": 90}


def _context(text: str, start: int, end: int, radius: int = 90) -> str:
    return re.sub(r"\s+", " ", text[max(0, start - radius):min(len(text), end + radius)]).strip()


def scan_brand_safety(text: str, source_url: str = "") -> dict[str, Any]:
    flags, risks, matches = [], {}, {}
    for category, terms in BLOCKLIST.items():
        category_matches = []
        for keyword, severity in terms:
            for match in re.finditer(rf"\b{re.escape(keyword)}\b", text or "", re.IGNORECASE):
                value = {"matched_keyword": match.group(0).casefold(), "category": category, "severity": severity,
                         "source_url": source_url, "context": _context(text, match.start(), match.end()),
                         "requires_llm_review": severity in {"high", "severe"}}
                flags.append(value)
                category_matches.append(value["matched_keyword"])
        risks[category] = bool(category_matches)
        matches[category] = list(dict.fromkeys(category_matches))
    reasons = [f"{flag['category']} evidence matched '{flag['matched_keyword']}' ({flag['severity']})" for flag in flags]
    if not reasons: reasons.append("No deterministic brand-safety keywords matched.")
    heuristic_score = brand_safety_score(flags)
    heuristic_risk = 100 - heuristic_score
    model_result = classify_with_model(
        "brand_safety",
        {"text": text or "", "source_url": source_url, "heuristic_flags": flags, "heuristic_risks": risks},
    )
    if model_result is not None:
        model_risk = model_result.risk_probability * 100
        risk_score = round(0.60 * model_risk + 0.40 * heuristic_risk, 2)
        score = float(max(0, min(100, 100 - risk_score)))
        if model_result.categories:
            flags.append({
                "matched_keyword": "model_classification",
                "category": "model_brand_safety",
                "severity": "high" if model_result.risk_probability >= 0.70 else "medium",
                "source_url": source_url,
                "context": "; ".join(model_result.reasons[:2]),
                "requires_llm_review": model_result.risk_probability >= 0.50,
                **model_result.to_evidence(),
            })
            reasons.extend(model_result.reasons)
    else:
        risk_score = round(heuristic_risk, 2)
        score = heuristic_score
    return {"risks": risks, "matches": matches, "flags": flags, "reasons": reasons, "source_url": source_url,
            "brand_safety_score": score, "heuristic_brand_safety_score": heuristic_score,
            "brand_safety_risk_score": risk_score,
            "model_brand_safety_probability": round(model_result.risk_probability, 4) if model_result is not None else None,
            "model_provider": model_result.provider if model_result is not None else None,
            "model_name": model_result.model if model_result is not None else None,
            "requires_llm_review": any(flag["requires_llm_review"] for flag in flags)}


def brand_safety_score(evidence: Any) -> float:
    if isinstance(evidence, dict):
        # Backward-compatible risk map: each active category is a medium flag.
        return float(max(0, 100 - 25 * sum(bool(value) for value in evidence.values())))
    flags = list(evidence or [])
    penalty = max((PENALTIES.get(str(flag.get("severity", "minor")), 15) for flag in flags), default=0)
    return float(max(0, 100 - penalty))
