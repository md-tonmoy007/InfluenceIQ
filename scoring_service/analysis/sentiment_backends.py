"""Pipeline 12 - Sentiment Score (multi-backend).

The role-5 sentiment pipeline prefers, in order:

1. :class:`VaderSentimentBackend` if the optional ``vaderSentiment``
   package is installed.
2. A small transformer backend if :mod:`transformers` is installed and a
   pre-trained sentiment model is available. We try the
   ``distilbert-base-uncased-finetuned-sst-2-english`` checkpoint
   (default) and fall back to lexicon if the model cannot be loaded.
3. The deterministic lexicon backend in
   :mod:`scoring_service.analysis.sentiment`.

All backends return a 0-100 raw score and the module wraps the result in
the same dict shape used by the rest of the role-5 pipeline. The
``adjusted_sentiment_score`` then multiplies the raw score by
``(1 - 0.50 * overall_fake_risk / 100)`` so fake comments do not create
fake positive sentiment.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from scoring_service.analysis.sentiment import score_text as lexicon_score
from scoring_service.scoring.normalize import clamp


class SentimentBackend(Protocol):
    name: str

    def score(self, text: str) -> float:
        """Return a 0-100 raw sentiment score."""


@dataclass
class LexiconBackend:
    name: str = "lexicon"

    def score(self, text: str) -> float:
        compound = lexicon_score(text)
        return round((compound + 1.0) * 50.0, 2)


@dataclass
class VaderBackend:
    name: str = "vader"

    def score(self, text: str) -> float:
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        except ImportError as exc:  # pragma: no cover - import guard
            raise RuntimeError("vaderSentiment is not installed") from exc
        analyzer = SentimentIntensityAnalyzer()
        return round((analyzer.polarity_scores(text or "")["compound"] + 1.0) * 50.0, 2)


@dataclass
class TransformerBackend:
    name: str = "transformer"
    model_name: str = "distilbert-base-uncased-finetuned-sst-2-english"

    def _pipeline(self) -> Any:
        from transformers import pipeline  # type: ignore
        return pipeline("sentiment-analysis", model=self.model_name)

    def score(self, text: str) -> float:
        if not text:
            return 50.0
        try:
            pipe = self._pipeline()
        except Exception:  # pragma: no cover - model load failure
            raise RuntimeError("transformer pipeline is unavailable")
        result = pipe(text[:512])[0]
        # SST-2 returns POSITIVE / NEGATIVE labels with a probability.
        score = float(result.get("score", 0.5))
        if str(result.get("label", "")).upper().startswith("NEG"):
            return round((1.0 - score) * 100.0, 2)
        return round(score * 100.0, 2)


def _select_backend(prefer: list[str] | None = None) -> SentimentBackend:
    """Pick the first available backend from the preference list."""
    preferences = prefer or ["vader", "transformer", "lexicon"]
    for name in preferences:
        if name == "vader":
            if importlib.util.find_spec("vaderSentiment") is not None:
                return VaderBackend()
        elif name == "transformer":
            if importlib.util.find_spec("transformers") is not None:
                try:
                    return TransformerBackend()
                except Exception:  # pragma: no cover - missing model weights
                    continue
        elif name == "lexicon":
            return LexiconBackend()
    return LexiconBackend()


def analyze_sentiment_multi(
    comments: list[Any] | None,
    overall_fake_risk_score: float | None = 0.0,
    *,
    backend: SentimentBackend | None = None,
    prefer: list[str] | None = None,
) -> dict[str, Any]:
    """Score the sentiment of a list of comments using a chosen backend.

    Returns a dict compatible with
    :func:`scoring_service.analysis.sentiment.analyze_sentiment` so
    downstream callers do not need to special-case the multi-backend
    path.
    """
    chosen = backend or _select_backend(prefer)
    texts = [str(item.get("text", "") if isinstance(item, dict) else item).strip()
             for item in comments or []]
    texts = [t for t in texts if t]
    raw_scores = [chosen.score(t) for t in texts] or [50.0]
    raw = round(sum(raw_scores) / len(raw_scores), 2)
    fake_risk = max(0.0, min(100.0, float(overall_fake_risk_score or 0)))
    adjusted = round(raw * (1 - 0.50 * fake_risk / 100), 2)
    return {
        "compound": round((raw / 50.0) - 1.0, 4),
        "raw_sentiment_score": raw,
        "sentiment_score": clamp(adjusted, 0, 100),
        "label": _label(adjusted),
        "sample_size": len(texts),
        "backend": chosen.name,
        "fake_risk_adjustment": round(raw - adjusted, 2),
        "reasons": ([f"Sentiment reduced by {raw - adjusted:.2f} points due to fake-engagement risk"]
                    if raw > adjusted else []),
    }


def _label(score: float) -> str:
    if score <= 30:
        return "negative"
    if score <= 60:
        return "mixed"
    if score <= 85:
        return "positive"
    return "strongly_positive"


__all__ = [
    "LexiconBackend",
    "SentimentBackend",
    "TransformerBackend",
    "VaderBackend",
    "_select_backend",
    "analyze_sentiment_multi",
]
