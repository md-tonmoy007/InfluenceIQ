"""`LLMExplainer`: thin wrapper over the active LLM explainer backend.

Consumed by the explainability-service. Builds a deterministic
prompt from a `(subject_id, factors, evidence_ids)` triple and
asks the configured LLM explainer to produce a human-readable
narrative. The wrapper never raises: any backend failure is
captured in the response's `mode` field so callers can surface
"stub" honestly in the UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models.registry import registry


@dataclass(frozen=True)
class ExplainerRequest:
    subject_id: str
    factors: dict[str, float]
    evidence_ids: Iterable[str]
    policy_version: str = "v1"


@dataclass(frozen=True)
class ExplainerResponse:
    text: str
    mode: str  # one of: "llm", "stub"


def _build_prompt(request: ExplainerRequest) -> str:
    factor_lines = "\n".join(
        f"- {key}: {value:.3f}" for key, value in sorted(request.factors.items())
    )
    evidence = ", ".join(request.evidence_ids) or "(no evidence ids supplied)"
    return (
        "You are the UMGL explainability assistant. Write a concise "
        "(3-5 sentence) human-readable explanation of why the risk "
        "score for the following subject is what it is. Use neutral, "
        "evidence-based language; do not speculate.\n\n"
        f"Subject: {request.subject_id}\n"
        f"Policy version: {request.policy_version}\n"
        f"Risk factors:\n{factor_lines or '- (no factors)'}\n"
        f"Evidence IDs: {evidence}\n"
    )


class LLMExplainer:
    def __init__(self) -> None:
        self._registry = registry()

    async def explain(self, request: ExplainerRequest) -> ExplainerResponse:
        prompt = _build_prompt(request)
        try:
            backend = self._registry.get(self._registry.resolve_name("llm"))
            predict = getattr(backend, "predict_text", None)
            if predict is None:
                return ExplainerResponse(
                    text="[stub] LLM backend exposes no predict_text method.",
                    mode="stub",
                )
            text = await predict(prompt, max_tokens=256, temperature=0.2)
        except Exception as exc:  # noqa: BLE001 — explainer is best-effort
            return ExplainerResponse(
                text=f"[stub] LLM explainer failed: {exc}",
                mode="stub",
            )
        if text.startswith("[stub:"):
            return ExplainerResponse(text=text, mode="stub")
        return ExplainerResponse(text=text, mode="llm")


__all__ = ["LLMExplainer", "ExplainerRequest", "ExplainerResponse"]
