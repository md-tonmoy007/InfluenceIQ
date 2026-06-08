from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


@dataclass(frozen=True)
class LLMRequest:
    task_type: str
    prompt: str
    max_tokens: int


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model: str
    fallback: bool


TASK_PROVIDER_AND_MODEL = {
    "generate_queries": ("GENERATE_QUERY_AI_PROVIDER", "GENERATE_QUERY_AI_MODEL"),
    "classify_brand_safety": (
        "CLASSIFY_BRAND_SAFETY_AI_PROVIDER",
        "CLASSIFY_BRAND_SAFETY_AI_MODEL",
    ),
    "resolve_identity_llm": ("RESOLVE_IDENTITY_AI_PROVIDER", "RESOLVE_IDENTITY_AI_MODEL"),
    "score_explain": ("SCORE_EXPLAIN_AI_PROVIDER", "SCORE_EXPLAIN_AI_MODEL"),
}


def available_provider_for(task_type: str) -> tuple[str, str] | None:
    setting_names = TASK_PROVIDER_AND_MODEL.get(task_type)
    if setting_names is None:
        return None

    provider_setting, model_setting = setting_names
    provider_name = getattr(settings, provider_setting, "").strip().lower()
    model_name = getattr(settings, model_setting, "").strip()

    if not provider_name or not model_name:
        return None
    if provider_name == "openrouter" and settings.OPENROUTER_API_KEY:
        return provider_name, model_name
    if provider_name == "gemini" and settings.GEMINI_API_KEY:
        return provider_name, model_name
    return None


def complete_or_fallback(request: LLMRequest, fallback_text: str) -> LLMResponse:
    provider = available_provider_for(request.task_type)
    if provider is None:
        return LLMResponse(
            text=fallback_text,
            provider="deterministic",
            model="fallback-v1",
            fallback=True,
        )

    provider_name, model = provider
    # Provider API calls intentionally land after the deterministic demo path is stable.
    return LLMResponse(text=fallback_text, provider=provider_name, model=model, fallback=True)
