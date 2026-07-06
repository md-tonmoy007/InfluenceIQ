from __future__ import annotations

import re
from typing import Any

_NEUTRAL_RELEVANCE_SCORE = 50.0


def relevance_score(candidate: dict[str, Any], campaign: dict[str, Any] | None = None) -> float:
    """Score 0-100 term overlap between campaign intent and candidate text.

    Falls back to a neutral score when the campaign's description and
    interests yield no comparable terms (e.g. an empty or very short
    ``search_query``) — there is no real candidate-side ``relevance``
    signal to read as a substitute, so a fixed neutral value is used
    rather than defaulting to 0.
    """
    campaign = campaign or {}
    campaign_text = " ".join(str(value) for value in [campaign.get("description", ""), *(campaign.get("interests") or [])])
    candidate_text = " ".join(str(value) for value in [candidate.get("context", ""), candidate.get("bio", ""), *(candidate.get("tags") or [])])
    terms = {term for term in re.findall(r"[a-z0-9]+", campaign_text.casefold()) if len(term) > 2}
    if not terms:
        return _NEUTRAL_RELEVANCE_SCORE
    overlap = len(terms & set(re.findall(r"[a-z0-9]+", candidate_text.casefold()))) / len(terms)
    return round(40 + overlap * 60, 2)
