"""External popularity and trend signal collection for deep analysis.

Collects Google Trends data, search visibility, and optional public-web
sentiment snippets. All external signals are secondary evidence — they
never form the sole basis for a recommendation.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.core.config import settings
from backend.pipeline.content.search_providers import search_web

log = logging.getLogger(__name__)


def collect_external_signals(
    creator_name: str,
    *,
    handle_variants: list[str] | None = None,
    topic_variants: list[str] | None = None,
) -> dict[str, Any]:
    """Gather Google Trends and search visibility evidence for a creator.

    Returns a structured payload with per-source coverage flags so the
    report synthesis layer can degrade confidence when a source is
    unavailable.
    """
    signals: dict[str, Any] = {
        "google_trends": None,
        "search_visibility": None,
        "web_sentiment": None,
        "_coverage": {
            "google_trends": "not_configured",
            "search_visibility": "not_configured",
            "web_sentiment": "not_configured",
        },
    }

    _collect_trends(signals, creator_name, handle_variants or [], topic_variants or [])
    _collect_search_visibility(signals, creator_name, handle_variants or [])
    _collect_web_sentiment(signals, creator_name, handle_variants or [])

    return signals


def _collect_trends(
    signals: dict[str, Any],
    creator_name: str,
    handle_variants: list[str],
    topic_variants: list[str],
) -> None:
    """Pull Google Trends data via pytrends if configured."""
    try:
        import pytrends
    except ImportError:
        signals["_coverage"]["google_trends"] = "unavailable"
        return

    # Try primary query (creator name)
    try:
        from pytrends.request import TrendReq

        pytrends_client = TrendReq(hl="en-US", tz=360, timeout=10)
    except Exception as exc:
        log.warning("Failed to init pytrends: %s", exc)
        signals["_coverage"]["google_trends"] = "error"
        return

    queries = [creator_name]
    if handle_variants:
        queries.extend(handle_variants[:3])
    if topic_variants:
        queries.extend(topic_variants[:3])

    try:
        pytrends_client.build_payload(queries[:5], timeframe="today 12-m")
        interest_over_time = pytrends_client.interest_over_time()
        if interest_over_time is not None and not interest_over_time.empty:
            signals["google_trends"] = {
                "interest_over_time": _trends_time_series(interest_over_time, queries),
                "compared_terms": queries[:5],
                "timeframe": "today 12-m",
            }
    except Exception as exc:
        log.warning("pytrends interest_over_time failed: %s", exc)

    try:
        pytrends_client.build_payload(queries[:5], timeframe="today 12-m")
        related = pytrends_client.related_queries()
        if related:
            summaries: dict[str, Any] = {}
            for term, data in related.items():
                if isinstance(data, dict):
                    top: list[dict[str, Any]] = []
                    rising: list[dict[str, Any]] = []
                    for df_label, df in data.items():
                        if df is None or df.empty:
                            continue
                        for _, row in df.head(10).iterrows():
                            entry = {"query": str(row.get("query", "")), "value": int(row.get("value", 0))}
                            if "rising" in str(df_label).lower():
                                rising.append(entry)
                            else:
                                top.append(entry)
                    summaries[term] = {"top": top, "rising": rising}
            if summaries:
                if signals["google_trends"] is None:
                    signals["google_trends"] = {}
                signals["google_trends"]["related_queries"] = summaries
    except Exception as exc:
        log.warning("pytrends related_queries failed: %s", exc)

    if signals["google_trends"] is not None:
        signals["_coverage"]["google_trends"] = "ok"
    else:
        signals["_coverage"]["google_trends"] = "no_data"


def _trends_time_series(df: Any, queries: list[str]) -> list[dict[str, Any]]:
    """Convert a pandas DataFrame from pytrends into a list of monthly snapshots."""
    points: list[dict[str, Any]] = []
    try:
        for idx, row in df.iterrows():
            point: dict[str, Any] = {"date": str(idx)}
            for q in queries:
                if q in row:
                    point[q] = int(row[q])
            points.append(point)
    except Exception:
        pass
    return points[-12:] if points else []


def _collect_search_visibility(
    signals: dict[str, Any],
    creator_name: str,
    handle_variants: list[str],
) -> None:
    """Query configured search providers for popularity evidence."""
    if not any([settings.BRAVE_SEARCH_API_KEY, settings.SERP_API_KEY]):
        signals["_coverage"]["search_visibility"] = "unavailable"
        return

    queries = [f'"{creator_name}" influencer', f"{creator_name} social media"]
    for handle in handle_variants[:2]:
        queries.append(f"{handle} creator")

    results_by_query: dict[str, list[dict[str, Any]]] = {}
    for query in queries[:5]:
        try:
            sr = search_web(query, limit=5)
            results_by_query[query] = [
                {
                    "url": r["url"],
                    "title": r["title"],
                    "snippet": r["snippet"],
                    "provider": r.get("provider", "unknown"),
                }
                for r in sr
            ]
        except Exception as exc:
            log.warning("search_visibility query=%s failed: %s", query, exc)
            results_by_query[query] = []

    if any(results_by_query.values()):
        signals["search_visibility"] = {"queries": results_by_query}
        signals["_coverage"]["search_visibility"] = "ok"
    else:
        signals["_coverage"]["search_visibility"] = "no_results"


def _collect_web_sentiment(
    signals: dict[str, Any],
    creator_name: str,
    handle_variants: list[str],
) -> None:
    """Optional search for reputation snippets (controversy, reviews, news)."""
    queries = [f"{creator_name} review", f"{creator_name} controversy"]
    for handle in handle_variants[:1]:
        queries.append(f"{handle} review")

    snippets: list[dict[str, Any]] = []
    for query in queries[:3]:
        try:
            sr = search_web(query, limit=3)
            for r in sr:
                snippet = r.get("snippet", "").strip()
                title = r.get("title", "").strip()
                if snippet or title:
                    snippets.append({
                        "url": r["url"],
                        "title": title,
                        "snippet": snippet,
                        "provider": r.get("provider", "unknown"),
                    })
        except Exception as exc:
            log.warning("web_sentiment query=%s failed: %s", query, exc)

    if snippets:
        signals["web_sentiment"] = {"snippets": snippets}
        signals["_coverage"]["web_sentiment"] = "ok"
    else:
        signals["_coverage"]["web_sentiment"] = "no_results"


__all__ = ["collect_external_signals"]
