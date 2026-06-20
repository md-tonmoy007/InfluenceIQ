"""Smoke tests for the optional ``umgl_ai`` integration.

These tests do not require ``umgl_ai`` to be installed. They verify the
graceful-degradation contract: when the package is not importable, every
v2 adapter returns the documented "no evidence" tuple, the LLM
explainer returns an empty string, and the import cache resets
correctly between test cases.
"""

from __future__ import annotations

import os
import sys


def test_try_import_returns_none_when_umgl_ai_missing(monkeypatch):
    """Without ``umgl_ai`` on ``sys.path`` the helper returns ``None`` and never raises."""
    from scoring_service.scoring.backends import umgl_ai_adapters as adp

    monkeypatch.delitem(sys.modules, "umgl_ai", raising=False)
    monkeypatch.setitem(sys.modules, "umgl_ai", None)
    adp.reset_import_cache()

    assert adp._try_import_umgl_ai() is None
    adp.reset_import_cache()


def test_semantic_v2_returns_none_when_flag_off():
    from scoring_service.scoring.backends import umgl_ai_adapters as adp

    adp.reset_import_cache()
    os.environ["UMGL_USE_SEMANTIC_V2"] = "0"
    score, versions = adp.semantic_v2_score({"bio": "ignored"})
    assert score is None
    assert versions == {}


def test_behavioral_v2_returns_none_when_flag_off():
    from scoring_service.scoring.backends import umgl_ai_adapters as adp

    adp.reset_import_cache()
    os.environ["UMGL_USE_BEHAVIORAL_V2"] = "0"
    score, versions = adp.behavioral_v2_score({})
    assert score is None
    assert versions == {}


def test_graph_v2_is_inert():
    from scoring_service.scoring.backends import umgl_ai_adapters as adp

    score, versions = adp.graph_v2_score({})
    assert score is None
    assert versions == {}


def test_bot_rings_v2_is_inert():
    from scoring_service.scoring.backends import umgl_ai_adapters as adp

    score, versions = adp.bot_rings_v2_score({})
    assert score is None
    assert versions == {}


def test_explain_via_llm_returns_empty_when_disabled():
    from scoring_service.scoring.backends import umgl_ai_adapters as adp

    os.environ["UMGL_USE_LLM_EXPLAINER"] = "0"
    text = adp.explain_via_llm("inf-1", {"relevance": 80.0})
    assert text == ""


def test_subject_id_for_is_deterministic():
    from scoring_service.scoring.backends import umgl_ai_adapters as adp

    first = adp.subject_id_for("influencer-42")
    second = adp.subject_id_for("influencer-42")
    other = adp.subject_id_for("influencer-99")
    assert first == second
    assert first != other
