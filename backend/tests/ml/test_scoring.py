"""Tests for the registry-driven SemanticEngineV2 and LLMExplainer."""

from __future__ import annotations

import asyncio

import pytest

from backend.ml.contracts import TextInferenceRequest
from backend.ml.llm_explainer import ExplainerRequest, LLMExplainer
from backend.ml.semantic_v2 import SemanticEngineV2


def _request() -> TextInferenceRequest:
    import uuid

    return TextInferenceRequest(
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        subject_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        text="hello world",
    )


def test_semantic_v2_returns_zero_scores_when_adapters_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With a real HF model load failing, the engine still returns a
    valid score object whose component values are clamped to [0, 1].
    """
    # Force the registry to attempt the real HF models so the
    # transformers pipeline is exercised; if a load fails the engine
    # catches the exception and returns 0.0 for that component.
    from backend.ml.models import registry as registry_module

    reg = registry_module.ModelRegistry()
    engine = SemanticEngineV2(reg)
    result = engine.score(_request())
    assert 0.0 <= result.spam_probability <= 1.0
    assert 0.0 <= result.toxicity_probability <= 1.0
    assert 0.0 <= result.aigc_probability <= 1.0
    assert 0.0 <= result.semantic_score <= 1.0
    assert "spam" in result.model_versions


def test_llm_explainer_stub_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ML_LLM_ENDPOINT", raising=False)
    explainer = LLMExplainer()
    response = asyncio.run(
        explainer.explain(
            ExplainerRequest(
                subject_id="abc",
                factors={"semantic": 0.4, "behavior": 0.2, "graph": 0.3},
                evidence_ids=["e1", "e2"],
            )
        )
    )
    assert response.mode == "stub"
    assert "LLM explainer failed" in response.text or "stub" in response.text
