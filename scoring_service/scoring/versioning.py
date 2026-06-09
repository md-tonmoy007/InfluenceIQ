"""Pipeline versioning helpers.

The role-5 spec uses the model version name ``Role5-FakeDetectionScore-v1``.
The previously shipped implementation registered the same model under
``Role5-FakeSignal-v1`` (the two are aliases). The :data:`MODEL_VERSION`
constant returns the canonical name and downstream components expose the
historical alias for backward compatibility with already-shipped
consumers.
"""

from __future__ import annotations

from datetime import UTC, datetime

# Canonical model name used in the role-5 spec and final output JSON.
MODEL_VERSION: str = "Role5-FakeDetectionScore-v1"

# Historical alias kept for back-compat with Role 3 / Role 4 consumers
# that already pinned the v1 FakeSignal identifier.
MODEL_VERSION_ALIAS: str = "Role5-FakeSignal-v1"

# Bumped to v2 when at least one optional v2 adapter (semantic /
# behavioral / graph / bot-rings) is active in the orchestrator. The
# LLM explainer is presentation-layer and does NOT bump the model
# version. Downstream consumers can detect the bump via the string
# itself; the v1 canonical name remains valid for the all-heuristics
# path.
MODEL_VERSION_V2: str = "Role5-FakeDetectionScore-v2"


def computed_at() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(UTC).isoformat()


def model_version_for(*, semantic_v2: bool, behavioral_v2: bool,
                      graph_v2: bool, bot_rings_v2: bool) -> str:
    """Return ``MODEL_VERSION_V2`` if any v2 adapter fired, else ``MODEL_VERSION``.

    The orchestrator calls this once per pipeline run, after the four
    signal-score helpers have reported whether they delegated to a v2
    adapter. The LLM explainer is intentionally excluded from the
    check — it does not change the underlying scoring model.
    """
    if any((semantic_v2, behavioral_v2, graph_v2, bot_rings_v2)):
        return MODEL_VERSION_V2
    return MODEL_VERSION


__all__ = [
    "MODEL_VERSION",
    "MODEL_VERSION_ALIAS",
    "MODEL_VERSION_V2",
    "computed_at",
    "model_version_for",
]
