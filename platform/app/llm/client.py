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


def available_provider_for(task_type: str) -> tuple[str, str] | None:
    if task_type == "generate_queries" and settings.MOONSHOT_API_KEY:
        return "moonshot", settings.KIMI_MODEL
    if task_type == "classify_brand_safety" and settings.GOOGLE_API_KEY:
        return "google", settings.GEMINI_MODEL
    if task_type == "resolve_identity_llm" and settings.DEEPSEEK_API_KEY:
        return "deepseek", settings.DEEPSEEK_MODEL
    if settings.OPENAI_API_KEY:
        return "openai", settings.OPENAI_JUDGE_MODEL
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
