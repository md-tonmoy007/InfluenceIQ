from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

import httpx

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
    task_routes = {
        "generate_queries": (settings.GENERATE_QUERY_AI_PROVIDER, settings.GENERATE_QUERY_AI_MODEL),
        "classify_brand_safety": (settings.CLASSIFY_BRAND_SAFETY_AI_PROVIDER, settings.CLASSIFY_BRAND_SAFETY_AI_MODEL),
        "resolve_identity_llm": (settings.RESOLVE_IDENTITY_AI_PROVIDER, settings.RESOLVE_IDENTITY_AI_MODEL),
        "score_explain": (settings.SCORE_EXPLAIN_AI_PROVIDER, settings.SCORE_EXPLAIN_AI_MODEL),
    }
    configured_provider, configured_model = task_routes.get(task_type, ("", ""))
    if configured_provider and configured_model:
        return configured_provider.strip().lower(), configured_model.strip()

    if task_type == "generate_queries" and settings.OPENROUTER_API_KEY:
        return "openrouter", settings.GENERATE_QUERY_AI_MODEL
    if task_type == "generate_queries" and settings.MOONSHOT_API_KEY:
        return "moonshot", settings.KIMI_MODEL
    if task_type == "classify_brand_safety" and (settings.GOOGLE_API_KEY or settings.GEMINI_API_KEY):
        return "google", settings.GEMINI_MODEL
    if task_type == "resolve_identity_llm" and settings.DEEPSEEK_API_KEY:
        return "deepseek", settings.DEEPSEEK_MODEL
    if settings.OPENAI_API_KEY:
        return "openai", settings.OPENAI_JUDGE_MODEL
    return None


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(part for part in parts if part)
    return str(content or "")


def _openrouter_complete(request: LLMRequest, model: str) -> str:
    response_format = {"type": "json_object"} if request.task_type == "generate_queries" else None
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "X-OpenRouter-Title": "InfluenceIQ",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a precise backend service. Follow the response format exactly."},
            {"role": "user", "content": request.prompt},
        ],
        "max_tokens": request.max_tokens,
        "temperature": 0.2,
    }
    if response_format is not None:
        payload["response_format"] = response_format

    url = f"{settings.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        body = response.json()

    choices = body.get("choices") or []
    if not choices:
        raise ValueError("OpenRouter returned no choices")
    message = choices[0].get("message") or {}
    text = _content_to_text(message.get("content"))
    if not text.strip():
        raise ValueError("OpenRouter returned empty content")
    return text


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
    try:
        if provider_name == "openrouter" and settings.OPENROUTER_API_KEY:
            return LLMResponse(
                text=_openrouter_complete(request, model),
                provider=provider_name,
                model=model,
                fallback=False,
            )
    except (httpx.HTTPError, ValueError, json.JSONDecodeError):
        pass

    return LLMResponse(text=fallback_text, provider=provider_name, model=model, fallback=True)
