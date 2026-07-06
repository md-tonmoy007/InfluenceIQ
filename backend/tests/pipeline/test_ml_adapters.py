"""Unit tests for :mod:`backend.pipeline.fusion.backends.ml_adapters`.

These tests do **not** require ``backend.ml`` to be installed. They cover
the env-flag short-circuits, the UUID helpers, the no-text path, and
the LLM-explainer disabled/empty path. A monkeypatched fake ``backend.ml``
module is used to cover the integration path.
"""

from __future__ import annotations

import sys
import types
import uuid

import pytest


@pytest.fixture(autouse=True)
def _reset_adapter_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset module-level state between tests."""
    from backend.pipeline.fusion.backends import ml_adapters as adp
    # Clear all UMGL_*_V2 flags so tests start from a known-off baseline.
    for name in (
        "ML_USE_SEMANTIC_V2",
        "ML_USE_BEHAVIORAL_V2",
        "ML_USE_GRAPH_V2",
        "ML_USE_BOT_RINGS_V2",
        "ML_USE_LLM_EXPLAINER",
    ):
        monkeypatch.delenv(name, raising=False)
    adp.reset_import_cache()
    # Re-read env flags (which we just cleared) so the module-level
    # constants reflect "off".
    monkeypatch.setattr(adp, "ML_USE_SEMANTIC_V2", False)
    monkeypatch.setattr(adp, "ML_USE_BEHAVIORAL_V2", False)
    monkeypatch.setattr(adp, "ML_USE_GRAPH_V2", False)
    monkeypatch.setattr(adp, "ML_USE_BOT_RINGS_V2", False)
    monkeypatch.setattr(adp, "ML_USE_LLM_EXPLAINER", False)


def test_subject_id_is_stable_uuid5() -> None:
    from backend.pipeline.fusion.backends import ml_adapters as adp
    a = adp.subject_id_for("influencer-42")
    b = adp.subject_id_for("influencer-42")
    assert a == b and isinstance(a, uuid.UUID)
    # Different inputs produce different UUIDs.
    assert adp.subject_id_for("influencer-99") != a


def test_tenant_id_defaults_to_zero_uuid() -> None:
    from backend.pipeline.fusion.backends import ml_adapters as adp
    assert adp.tenant_id_for({}) == adp.ZERO_UUID
    assert adp.tenant_id_for({"tenant_id": str(adp.ZERO_UUID)}) == adp.ZERO_UUID
    # A non-UUID string falls back to the zero UUID.
    assert adp.tenant_id_for({"tenant_id": "not-a-uuid"}) == adp.ZERO_UUID
    # A real UUID instance round-trips.
    real = uuid.uuid4()
    assert adp.tenant_id_for({"tenant_id": real}) == real


def test_try_import_returns_none_when_umgl_ai_missing() -> None:
    from backend.pipeline.fusion.backends import ml_adapters as adp
    # Force the import attempt to fail by pre-seeding the cache with None.
    adp._ML_CACHE["module"] = None
    assert adp._try_import_ml() is None


def test_semantic_v2_returns_none_when_flag_off() -> None:
    from backend.pipeline.fusion.backends import ml_adapters as adp
    assert adp.ML_USE_SEMANTIC_V2 is False
    assert adp.semantic_v2_score({"bio": "hi"}) == (None, {})


def test_semantic_v2_returns_none_when_text_empty() -> None:
    from backend.pipeline.fusion.backends import ml_adapters as adp
    adp.ML_USE_SEMANTIC_V2 = True
    adp._ML_CACHE["module"] = None  # even if importable, no text means no call
    assert adp.semantic_v2_score({}) == (None, {})


def test_behavioral_v2_returns_none_when_flag_off() -> None:
    from backend.pipeline.fusion.backends import ml_adapters as adp
    assert adp.ML_USE_BEHAVIORAL_V2 is False
    assert adp.behavioral_v2_score({}) == (None, {})


def test_graph_and_bot_rings_v2_are_inert_in_v1() -> None:
    from backend.pipeline.fusion.backends import ml_adapters as adp
    adp.ML_USE_GRAPH_V2 = True
    adp.ML_USE_BOT_RINGS_V2 = True
    assert adp.graph_v2_score({}) == (None, {})
    assert adp.bot_rings_v2_score({}) == (None, {})


def test_explain_via_llm_disabled_returns_empty() -> None:
    from backend.pipeline.fusion.backends import ml_adapters as adp
    assert adp.ML_USE_LLM_EXPLAINER is False
    assert adp.explain_via_llm("i-1", {"relevance": 80.0}) == ""


def test_semantic_v2_dispatches_with_fake_ml(monkeypatch: pytest.MonkeyPatch) -> None:
    """When a fake backend.ml module is installed via sys.modules, the
    adapter delegates and returns a (0-100, versions) tuple."""
    from backend.pipeline.fusion.backends import ml_adapters as adp

    # Build a tiny fake backend.ml package on sys.modules.
    fake_pkg = types.ModuleType("backend.ml")
    fake_contracts = types.ModuleType("backend.ml.contracts")
    fake_models = types.ModuleType("backend.ml.models")
    fake_registry_mod = types.ModuleType("backend.ml.models.registry")
    fake_semantic_v2_mod = types.ModuleType("backend.ml.semantic_v2")

    class _FakeTextRequest:
        def __init__(self, tenant_id, subject_id, text, language=None):
            self.tenant_id = tenant_id
            self.subject_id = subject_id
            self.text = text

    class _FakeSemanticScore:
        def __init__(self, subject_id, semantic_score, model_versions):
            self.subject_id = subject_id
            self.semantic_score = semantic_score
            self.model_versions = model_versions

    class _FakeEngine:
        def __init__(self, registry):
            self.registry = registry

        def score(self, request):
            assert isinstance(request.tenant_id, uuid.UUID)
            assert isinstance(request.subject_id, uuid.UUID)
            return _FakeSemanticScore(
                subject_id=request.subject_id,
                semantic_score=0.42,
                model_versions={"spam": "fake-distilbert", "toxicity": "fake-toxic"},
            )

    class _FakeRegistry:
        def __call__(self):
            return self

    fake_contracts.TextInferenceRequest = _FakeTextRequest
    fake_registry_mod.registry = _FakeRegistry
    fake_semantic_v2_mod.SemanticEngineV2 = _FakeEngine

    monkeypatch.setitem(sys.modules, "backend.ml", fake_pkg)
    monkeypatch.setitem(sys.modules, "backend.ml.contracts", fake_contracts)
    monkeypatch.setitem(sys.modules, "backend.ml.models", fake_models)
    monkeypatch.setitem(sys.modules, "backend.ml.models.registry", fake_registry_mod)
    monkeypatch.setitem(sys.modules, "backend.ml.semantic_v2", fake_semantic_v2_mod)
    adp.reset_import_cache()
    adp.ML_USE_SEMANTIC_V2 = True

    score_value, versions = adp.semantic_v2_score(
        {"bio": "Spam-like content"}, candidate={"influencer_id": "i-99"},
    )
    assert score_value == pytest.approx(42.0)  # 0.42 * 100
    assert versions == {"spam": "fake-distilbert", "toxicity": "fake-toxic"}


def test_signal_score_with_provenance_falls_back_to_heuristic() -> None:
    """With the v2 flag off, the v2-aware variant in risk_components
    runs the heuristic body and reports used_v2=False."""
    from backend.pipeline.fusion.components import (
        behavioral_signal_score_with_provenance,
        semantic_signal_score_with_provenance,
    )
    score, used, versions = semantic_signal_score_with_provenance({
        "spam_probability": 0.5, "toxicity_probability": 0.2,
    })
    assert used is False
    assert versions == {}
    assert score is not None and 0 <= score <= 100

    score, used, versions = behavioral_signal_score_with_provenance(
        scores={"fake_follower_risk_score": 30, "fake_comment_risk_score": 10, "bot_behavior_risk_score": 5},
        features={"posting_interval_uniformity": 0.4, "night_activity_ratio": 0.1},
    )
    assert used is False
    assert versions == {}
    assert score is not None


def test_semantic_v2_exception_logs_warning(monkeypatch, caplog):
    """When the engine raises, a warning is logged and the adapter returns (None, {})."""
    from backend.pipeline.fusion.backends import ml_adapters as adp

    adp.ML_USE_SEMANTIC_V2 = True
    adp._ML_CACHE["module"] = "force_success"

    fake_pkg = types.ModuleType("backend.ml")
    fake_contracts = types.ModuleType("backend.ml.contracts")
    fake_models = types.ModuleType("backend.ml.models")
    fake_registry_mod = types.ModuleType("backend.ml.models.registry")
    fake_semantic_v2_mod = types.ModuleType("backend.ml.semantic_v2")

    class _FakeRequest:
        pass

    fake_contracts.TextInferenceRequest = _FakeRequest
    fake_registry_mod.registry = lambda: None

    class _RaisingEngine:
        def __init__(self, registry):
            pass

        def score(self, request):
            raise RuntimeError("simulated engine crash")

    fake_semantic_v2_mod.SemanticEngineV2 = _RaisingEngine

    monkeypatch.setitem(sys.modules, "backend.ml", fake_pkg)
    monkeypatch.setitem(sys.modules, "backend.ml.contracts", fake_contracts)
    monkeypatch.setitem(sys.modules, "backend.ml.models", fake_models)
    monkeypatch.setitem(sys.modules, "backend.ml.models.registry", fake_registry_mod)
    monkeypatch.setitem(sys.modules, "backend.ml.semantic_v2", fake_semantic_v2_mod)
    adp.reset_import_cache()

    score_value, versions = adp.semantic_v2_score(
        {"bio": "test"}, candidate={"influencer_id": "i-1"},
    )
    assert score_value is None
    assert versions == {}
    assert any("semantic_v2_score failed" in rec.message for rec in caplog.records)


def test_behavioral_v2_exception_logs_warning(monkeypatch, caplog):
    """When the engine raises, a warning is logged and the adapter returns (None, {})."""
    from backend.pipeline.fusion.backends import ml_adapters as adp

    adp.ML_USE_BEHAVIORAL_V2 = True
    adp._ML_CACHE["module"] = "force_success"

    fake_pkg = types.ModuleType("backend.ml")
    fake_contracts = types.ModuleType("backend.ml.contracts")
    fake_behavioral_mod = types.ModuleType("backend.ml.behavioral")

    class _FakeFeatures:
        pass

    fake_contracts.BehaviorFeatures = _FakeFeatures

    class _RaisingEngine:
        def score(self, request):
            raise RuntimeError("simulated engine crash")

    fake_behavioral_mod.BehavioralEngine = _RaisingEngine

    monkeypatch.setitem(sys.modules, "backend.ml", fake_pkg)
    monkeypatch.setitem(sys.modules, "backend.ml.contracts", fake_contracts)
    monkeypatch.setitem(sys.modules, "backend.ml.behavioral", fake_behavioral_mod)
    adp.reset_import_cache()

    score_value, versions = adp.behavioral_v2_score(
        {"posts_per_hour": 10}, candidate={"influencer_id": "i-1"},
    )
    assert score_value is None
    assert versions == {}
    assert any("behavioral_v2_score failed" in rec.message for rec in caplog.records)


def test_explain_via_llm_exception_logs_warning(monkeypatch, caplog):
    """When the explainer raises, a warning is logged and the adapter returns ''."""
    import asyncio

    from backend.pipeline.fusion.backends import ml_adapters as adp

    adp.ML_USE_LLM_EXPLAINER = True
    adp._ML_CACHE["module"] = "force_success"

    fake_pkg = types.ModuleType("backend.ml")
    fake_llm_mod = types.ModuleType("backend.ml.llm_explainer")

    class _FakeRequest:
        pass

    fake_llm_mod.ExplainerRequest = _FakeRequest

    class _RaisingExplainer:
        def explain(self, request):
            raise RuntimeError("simulated explainer crash")

    fake_llm_mod.LLMExplainer = _RaisingExplainer

    monkeypatch.setitem(sys.modules, "backend.ml", fake_pkg)
    monkeypatch.setitem(sys.modules, "backend.ml.llm_explainer", fake_llm_mod)
    adp.reset_import_cache()

    result = adp.explain_via_llm("i-1", {"relevance": 80})
    assert result == ""
    assert any("explain_via_llm failed" in rec.message for rec in caplog.records)
