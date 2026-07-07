"""OpenRouter (OpenAI-compatible) LLM adapter.

Calls the OpenRouter chat-completions API configured by
`ML_LLM_ENDPOINT` (base URL, default ``https://openrouter.ai/api/v1``)
and `OPENROUTER_API_KEY`. The model defaults to `UMGL_LLM_MODEL` but
callers may override per-request via the ``model`` kwarg (query
planning passes the value of `AI_AGENT_LLM_QUERY_PLANNING`).

Honest-fallback contract (same as the Llama adapter): any non-2xx
response, transport error, or empty body yields a ``[stub:...]``
string so callers can detect degradation and fall back deterministically
instead of crashing.

The adapter also exposes ``embed_text`` for relevance embeddings via
OpenRouter's ``/embeddings`` route. A deterministic hash-based stub
vector is returned when OPENROUTER_API_KEY is absent.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

import httpx

from .base import ModelInfo

_BASE = os.getenv("ML_LLM_ENDPOINT") or "https://openrouter.ai/api/v1"
_MODEL = os.getenv("UMGL_LLM_MODEL", "openai/gpt-oss-20b:free")
_TIMEOUT = float(os.getenv("UMGL_LLM_TIMEOUT_SECS", "30"))
_EMBEDDING_MODEL = os.getenv("UMGL_EMBEDDING_MODEL", "text-embedding-3-small")
_EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))


class OpenRouterAdapter:
    def __init__(self) -> None:
        self._base = _BASE.rstrip("/")
        self._model = _MODEL
        self._api_key = os.getenv("OPENROUTER_API_KEY", "")

    def info(self) -> ModelInfo:
        return ModelInfo(
            name="openrouter",
            version=self._model,
            family="llm",
            loaded=bool(self._api_key),
            notes=f"endpoint={self._base}",
        )

    async def predict_text(self, prompt: str, **kwargs: Any) -> str:
        model = str(kwargs.get("model") or self._model)
        max_tokens = int(kwargs.get("max_tokens", 256))
        temperature = float(kwargs.get("temperature", 0.2))
        if not self._api_key:
            return self._stub(prompt, reason="no OPENROUTER_API_KEY")
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.post(
                    f"{self._base}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                )
            if response.status_code >= 400:
                return self._stub(prompt, reason=f"http {response.status_code}: {response.text[:200]}")
            payload = response.json()
            choices = payload.get("choices") or []
            if not choices:
                return self._stub(prompt, reason="no choices")
            text = (choices[0].get("message") or {}).get("content") or ""
            if not text:
                return self._stub(prompt, reason="empty content")
            return text
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            return self._stub(prompt, reason=str(exc))

    def _stub(self, prompt: str, reason: str) -> str:
        head = (prompt.strip().splitlines()[:1] or [prompt])[0][:240]
        return f"[stub:{reason}] OpenRouter unavailable. Input head: {head!r}"

    async def embed_text(self, text: str, **kwargs: Any) -> list[float]:
        model = str(kwargs.get("model") or _EMBEDDING_MODEL)
        if not self._api_key:
            return self._hash_stub(text)
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.post(
                    f"{self._base}/embeddings",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={"model": model, "input": text},
                )
            if response.status_code >= 400:
                return self._hash_stub(text)
            payload = response.json()
            data = payload.get("data") or []
            if not data:
                return self._hash_stub(text)
            embedding = data[0].get("embedding") or []
            return [float(v) for v in embedding]
        except (httpx.HTTPError, json.JSONDecodeError):
            return self._hash_stub(text)

    def _hash_stub(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        raw = [b / 255.0 for b in digest]
        expanded: list[float] = []
        while len(expanded) < _EMBEDDING_DIM:
            expanded.extend(raw)
        vec = expanded[:_EMBEDDING_DIM]
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [x / norm for x in vec]


__all__ = ["OpenRouterAdapter"]
