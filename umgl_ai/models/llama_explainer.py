"""Llama 3.1 explainer adapter.

Calls a vLLM / Ollama / TGI HTTP endpoint configured by
`UMGL_LLM_ENDPOINT`. The endpoint must accept a JSON body of
`{"prompt": "...", "max_tokens": ..., "temperature": ...}` and
return `{"text": "..."}`. Any non-2xx response is treated as a
fallback trigger; the adapter then returns a templated stub so
callers always get a coherent explanation string back.

The base URL defaults to a local Ollama daemon. When
`UMGL_LLM_ENDPOINT` is unset the adapter stays in a stub-only
mode and returns a deterministic explanation scaffold derived
from the input prompt's first 240 characters; this is exactly the
behaviour the explainability-service expects when no LLM is
configured.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from .base import ModelInfo

_ENDPOINT = os.getenv("UMGL_LLM_ENDPOINT", "http://localhost:11434/api/generate")
_MODEL = os.getenv("UMGL_LLM_MODEL", "llama3.1:8b-instruct")
_TIMEOUT = float(os.getenv("UMGL_LLM_TIMEOUT_SECS", "30"))


class LlamaExplainerAdapter:
    def __init__(self) -> None:
        self._endpoint = _ENDPOINT
        self._model = _MODEL

    def info(self) -> ModelInfo:
        return ModelInfo(
            name="llama_explainer",
            version=self._model,
            family="llm",
            loaded=bool(self._endpoint),
            notes=f"endpoint={self._endpoint}",
        )

    async def predict_text(self, prompt: str, **kwargs: Any) -> str:
        max_tokens = int(kwargs.get("max_tokens", 256))
        temperature = float(kwargs.get("temperature", 0.2))
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.post(
                    self._endpoint,
                    json={
                        "model": self._model,
                        "prompt": prompt,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "stream": False,
                    },
                )
            if response.status_code >= 400:
                return self._stub(prompt, reason=f"http {response.status_code}")
            payload = response.json()
            text = payload.get("text") or payload.get("response") or ""
            if not text:
                return self._stub(prompt, reason="empty response")
            return text
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            return self._stub(prompt, reason=str(exc))

    def _stub(self, prompt: str, reason: str) -> str:
        snippet = prompt.strip().splitlines()[:1] or [prompt]
        head = snippet[0][:240]
        return (
            f"[stub:{reason}] LLM endpoint unavailable. The first 240 "
            f"characters of the input were: {head!r}"
        )


__all__ = ["LlamaExplainerAdapter"]
