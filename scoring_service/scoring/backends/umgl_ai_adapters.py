"""Optional adapter layer for the reference ``umgl_ai`` ML package.

This module lets :mod:`scoring_service.scoring.risk_components` and the
Celery adapter in :mod:`platform.app.tasks.score` opt in to model-backed
versions of the heuristic pipelines. When all flags are off (the
default) nothing is imported and behaviour is byte-for-byte identical
to the pre-upgrade heuristics.

Environment flags
=================

``UMGL_USE_SEMANTIC_V2``     - 1 enables the registry-driven semantic engine
                                (:class:`umgl_ai.semantic_v2.SemanticEngineV2`).
``UMGL_USE_BEHAVIORAL_V2``   - 1 enables the calibrated behavioral engine
                                (:class:`umgl_ai.behavioral.BehavioralEngine`).
``UMGL_USE_GRAPH_V2``        - declared but inert in v1 (needs
                                :class:`umgl_ai.contracts.GraphEdge` extraction).
``UMGL_USE_BOT_RINGS_V2``    - declared but inert in v1 (same reason).
``UMGL_USE_LLM_EXPLAINER``   - 1 enables the LLM natural-language explainer
                                (:class:`umgl_ai.llm_explainer.LLMExplainer`)
                                called from the Celery adapter, not the
                                orchestrator.

Adapter shape
=============

All v2 scoring adapters return ``(float | None, dict[str, str])`` where
the float is the **0-100** signal score and the dict is the
``model_versions`` provenance. ``None`` means "no evidence / not
available" and lets the existing ``*_signal_score`` heuristic body take
over.

The :func:`explain_via_llm` helper returns a non-empty string only when
the explainer actually produced text; callers should treat ``""`` as
"explain not available, fall back to the deterministic summary".
"""

from __future__ import annotations

import os
import uuid
from typing import Any

# ---------------------------------------------------------------------------
# Feature flags — read once at import time. Cheap and deterministic.
# ---------------------------------------------------------------------------

_TRUE_SET = frozenset({"1", "true", "yes", "on"})


def _flag(name: str) -> bool:
    return os.environ.get(name, "0").strip().lower() in _TRUE_SET


UMGL_USE_SEMANTIC_V2: bool = _flag("UMGL_USE_SEMANTIC_V2")
UMGL_USE_BEHAVIORAL_V2: bool = _flag("UMGL_USE_BEHAVIORAL_V2")
UMGL_USE_GRAPH_V2: bool = _flag("UMGL_USE_GRAPH_V2")
UMGL_USE_BOT_RINGS_V2: bool = _flag("UMGL_USE_BOT_RINGS_V2")
UMGL_USE_LLM_EXPLAINER: bool = _flag("UMGL_USE_LLM_EXPLAINER")


# ---------------------------------------------------------------------------
# UUID helpers. umgl_ai contracts require UUIDs for tenant_id and
# subject_id; we never want a per-process hash() result (PYTHONHASHSEED
# randomises it) so we use uuid5 over a stable namespace.
# ---------------------------------------------------------------------------

ZERO_UUID: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000000")
SUBJECT_NS: uuid.UUID = uuid.NAMESPACE_URL


def subject_id_for(influencer_id: str | int) -> uuid.UUID:
    """Return a stable UUID5 derived from an influencer identifier.

    Two calls with the same ``influencer_id`` always return the same
    UUID, even across processes and Python versions.
    """
    return uuid.uuid5(SUBJECT_NS, f"role5:{influencer_id}")


def tenant_id_for(candidate: dict[str, Any]) -> uuid.UUID:
    """Return the tenant UUID for a candidate.

    The candidate dict may carry ``tenant_id`` as a UUID, a UUID-shaped
    string, or a plain string. Anything unparseable falls back to the
    well-known zero UUID so the call never raises. The "absence of
    evidence" semantics mirror the spec's SAFE-default rule.
    """
    raw = candidate.get("tenant_id") if isinstance(candidate, dict) else None
    if isinstance(raw, uuid.UUID):
        return raw
    if isinstance(raw, str) and raw:
        try:
            return uuid.UUID(raw)
        except (TypeError, ValueError):
            pass
    return ZERO_UUID


# ---------------------------------------------------------------------------
# Lazy import cache. umgl_ai pulls in torch, transformers, peft, etc.
# We never want to pay that cost unless an operator opts in. The cache
# stores one of:
#   * the umgl_ai module, on success
#   * None, after a failed import attempt (we don't retry on every call)
#   * the sentinel "unknown" before the first attempt
# ---------------------------------------------------------------------------

_UNKNOWN: Any = object()
_UMGL_AI_CACHE: dict[str, Any] = {"module": _UNKNOWN}


def reset_import_cache() -> None:
    """Reset the import cache. Tests call this between cases."""
    _UMGL_AI_CACHE["module"] = _UNKNOWN


def _try_import_umgl_ai() -> Any | None:
    """Return the umgl_ai module or None. Result is cached for the process lifetime."""
    cached = _UMGL_AI_CACHE.get("module", _UNKNOWN)
    if cached is not _UNKNOWN:
        return cached
    try:
        import umgl_ai  # type: ignore[import-not-found]
    except Exception:
        _UMGL_AI_CACHE["module"] = None
        return None
    _UMGL_AI_CACHE["module"] = umgl_ai
    return umgl_ai


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------


def _join_text(features: dict[str, Any], *keys: str) -> str:
    """Concatenate the named text fields, returning the stripped result."""
    return " ".join(str(features.get(k, "")) for k in keys).strip()


def semantic_v2_score(features: dict[str, Any], *,
                      candidate: dict[str, Any] | None = None) -> tuple[float | None, dict[str, str]]:
    """Run the registry-driven semantic engine, returning (0-100 score, model_versions).

    Returns ``(None, {})`` when the flag is off, umgl_ai is not
    importable, no text is available, or the engine raised. Never
    raises.
    """
    if not UMGL_USE_SEMANTIC_V2:
        return None, {}
    umgl_ai = _try_import_umgl_ai()
    if umgl_ai is None:
        return None, {}
    text = _join_text(features, "bio", "content", "context")
    if not text:
        return None, {}
    try:
        from umgl_ai.contracts import TextInferenceRequest
        from umgl_ai.models.registry import registry
        from umgl_ai.semantic_v2 import SemanticEngineV2

        cand = candidate if isinstance(candidate, dict) else features
        request = TextInferenceRequest(
            tenant_id=tenant_id_for(cand),
            subject_id=subject_id_for(str(cand.get("influencer_id", "anonymous"))),
            text=text[:100_000],
        )
        result = SemanticEngineV2(registry()).score(request)
        return round(float(result.semantic_score) * 100.0, 2), dict(result.model_versions)
    except Exception:
        return None, {}


def behavioral_v2_score(features: dict[str, Any], *,
                        candidate: dict[str, Any] | None = None) -> tuple[float | None, dict[str, str]]:
    """Run the calibrated behavioral engine, returning (0-100 score, model_versions).

    Maps the heuristic feature names the candidate dict already carries
    onto the :class:`umgl_ai.contracts.BehaviorFeatures` Pydantic model.
    Returns ``(None, {})`` when the flag is off, the import fails, or the
    engine raised. Never raises.
    """
    if not UMGL_USE_BEHAVIORAL_V2:
        return None, {}
    umgl_ai = _try_import_umgl_ai()
    if umgl_ai is None:
        return None, {}

    def _opt(name: str, default: float = 0.0) -> float:
        value = features.get(name)
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    try:
        from umgl_ai.behavioral import BehavioralEngine
        from umgl_ai.contracts import BehaviorFeatures

        cand = candidate if isinstance(candidate, dict) else features
        request = BehaviorFeatures(
            tenant_id=tenant_id_for(cand),
            subject_id=subject_id_for(str(cand.get("influencer_id", "anonymous"))),
            posts_per_hour=_opt("posts_per_hour"),
            median_session_minutes=_opt("median_session_minutes"),
            account_age_days=_opt("account_age_days"),
            engagement_velocity=_opt("engagement_velocity"),
            follower_growth_per_day=_opt("follower_growth_per_day"),
            duplicate_comment_ratio=_opt("duplicate_comment_ratio"),
            posting_interval_cv=_opt("posting_interval_cv"),
            night_activity_ratio=_opt("night_activity_ratio"),
        )
        result = BehavioralEngine().score(request)
        return round(float(result.behavior_score) * 100.0, 2), {k: str(v) for k, v in (result.model_version and {"behavior": result.model_version} or {}).items()}
    except Exception:
        return None, {}


def graph_v2_score(features: dict[str, Any], *,
                   candidate: dict[str, Any] | None = None) -> tuple[float | None, dict[str, str]]:
    """Inert in v1 — requires ``GraphEdge`` extraction from the candidate dict.

    Returns ``(None, {})`` unconditionally. The flag is honoured by the
    helper above but the engine call is a no-op until
    :func:`extract_interaction_edges` lands in a follow-up.
    """
    return None, {}


def bot_rings_v2_score(features: dict[str, Any], *,
                       candidate: dict[str, Any] | None = None) -> tuple[float | None, dict[str, str]]:
    """Inert in v1 — requires ``GraphEdge`` extraction. See :func:`graph_v2_score`."""
    return None, {}


# ---------------------------------------------------------------------------
# LLM explainer — called from the Celery adapter, not the orchestrator.
# ---------------------------------------------------------------------------


def explain_via_llm(influencer_id: str | int, factors: dict[str, float], *,
                    evidence_ids: list[str] | None = None) -> str:
    """Return a natural-language explanation or ``""`` when unavailable.

    Sync wrapper around the async :class:`LLMExplainer`. Uses
    :func:`asyncio.run` so the Celery adapter can call it from a sync
    ``@shared_task`` body. The orchestrator stays free of LLM I/O.
    """
    if not UMGL_USE_LLM_EXPLAINER:
        return ""
    umgl_ai = _try_import_umgl_ai()
    if umgl_ai is None:
        return ""
    try:
        import asyncio
        from umgl_ai.llm_explainer import ExplainerRequest, LLMExplainer

        cleaned_factors: dict[str, float] = {}
        for key, value in (factors or {}).items():
            try:
                cleaned_factors[str(key)] = round(float(value), 2)
            except (TypeError, ValueError):
                continue

        request = ExplainerRequest(
            subject_id=str(influencer_id),
            factors=cleaned_factors,
            evidence_ids=list(evidence_ids or []),
        )
        response = asyncio.run(LLMExplainer().explain(request))
        return str(getattr(response, "text", "") or "")
    except Exception:
        return ""


__all__ = [
    "SUBJECT_NS",
    "UMGL_USE_BEHAVIORAL_V2",
    "UMGL_USE_BOT_RINGS_V2",
    "UMGL_USE_GRAPH_V2",
    "UMGL_USE_LLM_EXPLAINER",
    "UMGL_USE_SEMANTIC_V2",
    "ZERO_UUID",
    "behavioral_v2_score",
    "bot_rings_v2_score",
    "explain_via_llm",
    "graph_v2_score",
    "reset_import_cache",
    "semantic_v2_score",
    "subject_id_for",
    "tenant_id_for",
]
