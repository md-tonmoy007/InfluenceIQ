from __future__ import annotations

from typing import Any


def build_reasons(analyses: dict[str, dict[str, Any]]) -> dict[str, Any]:
    positive, negative, evidence = [], [], {}
    for name, analysis in analyses.items():
        if name == "credibility":
            positive.extend(analysis.get("positive_reasons", []))
            negative.extend(analysis.get("negative_reasons", []))
        elif name == "brand_safety" and analysis.get("brand_safety_score", 100) >= 85:
            positive.append("Brand safety score is strong")
        else:
            negative.extend(analysis.get("reasons", []))
        if analysis.get("evidence"):
            evidence[name] = analysis["evidence"]
        if analysis.get("flags"):
            evidence[name] = analysis["flags"]
    return {"positive_reasons": list(dict.fromkeys(positive)), "negative_reasons": list(dict.fromkeys(negative)),
            "evidence": evidence}


def build_summary(grade: str, confidence: str, positive_reasons: list[str], negative_reasons: list[str], risk_category: str) -> str:
    if risk_category in {"HIGH_RISK", "BOT_LIKE", "SPAM_RING"}:
        detail = ", ".join(reason.rstrip(".") for reason in negative_reasons[:3]) or "multiple elevated fake-activity signals"
        return f"Account classified as {risk_category} because {detail}."
    positive = ", ".join(reason.rstrip(".") for reason in positive_reasons[:2]) or "limited positive evidence"
    negative = ", ".join(reason.rstrip(".") for reason in negative_reasons[:2])
    suffix = f" However, {negative}." if negative else ""
    return f"Influencer classified as {grade} with {confidence} confidence because of {positive}.{suffix}"
