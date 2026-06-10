from __future__ import annotations

from app.config import settings

TOKEN_BUDGETS = {
    "generate_queries": settings.TOKEN_BUDGET_QUERY_GEN,
    "classify_brand_safety": settings.TOKEN_BUDGET_BRAND_SAFETY,
    "resolve_identity_llm": settings.TOKEN_BUDGET_IDENTITY_RESOLUTION,
    "score_explain": settings.TOKEN_BUDGET_SCORE_EXPLAIN,
}


def token_budget_for(task_type: str) -> int:
    try:
        return TOKEN_BUDGETS[task_type]
    except KeyError as exc:
        raise ValueError(f"Unknown LLM task type: {task_type}") from exc


def assert_within_budget(task_type: str, estimated_tokens: int) -> None:
    budget = token_budget_for(task_type)
    if estimated_tokens > budget:
        raise ValueError(f"{task_type} estimated tokens {estimated_tokens} exceeds budget {budget}")
