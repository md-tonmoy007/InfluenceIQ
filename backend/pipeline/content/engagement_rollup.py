"""Per-platform recent-engagement roll-up.

Computes normalised per-post view/like/comment averages from a
:class:`PlatformProfile` so the same metrics mean the same thing
across YouTube, Instagram, and TikTok.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def compute_recent_engagement(profile: Any) -> dict[str, Any]:
    """Return a roll-up dict for *profile* and its ``profile.posts`` list.

    Each post dict may carry ``view_count`` (int), ``like_count`` (int),
    ``comment_count`` (int), and ``published_at`` (ISO-8601 str).  The
    function always returns a dict with the keys below — individual
    values will be ``None`` when no post in the window provides them.
    """

    posts: list[dict[str, Any]] = list(getattr(profile, "posts", []) or [])
    followers = getattr(profile, "followers", None)
    lifetime_views = (
        (getattr(profile, "raw", {}) or {}).get("lifetime_views")
    )

    sorted_posts = sorted(posts, key=_published_sort_key, reverse=True)

    view_values: list[int] = []
    like_values: list[int] = []
    comment_values: list[int] = []
    timestamps: list[datetime] = []

    for post in sorted_posts:
        vc = _int_or_none(post.get("view_count") or post.get("views"))
        lc = _int_or_none(post.get("like_count") or post.get("likes"))
        cc = _int_or_none(post.get("comment_count") or post.get("comments"))
        if vc is not None:
            view_values.append(vc)
        if lc is not None:
            like_values.append(lc)
        if cc is not None:
            comment_values.append(cc)
        ts = _parse_ts(post.get("published_at"))
        if ts is not None:
            timestamps.append(ts)

    recent_views = int(sum(view_values) / len(view_values)) if view_values else None
    recent_likes = int(sum(like_values) / len(like_values)) if like_values else None
    recent_comments = int(sum(comment_values) / len(comment_values)) if comment_values else None

    recent_engagement_rate: float | None = None
    if followers and followers > 0:
        numerator = (
            (recent_likes or 0)
            + (recent_comments or 0)
        )
        if numerator > 0:
            recent_engagement_rate = round(numerator / followers, 6)

    recent_window_days: int | None = None
    if len(timestamps) >= 2:
        recent_window_days = (timestamps[0] - timestamps[-1]).days
    elif timestamps:
        recent_window_days = 0

    return {
        "recent_views": recent_views,
        "recent_likes": recent_likes,
        "recent_comments": recent_comments,
        "recent_engagement_rate": recent_engagement_rate,
        "lifetime_views": _int_or_none(lifetime_views),
        "recent_window_days": recent_window_days,
    }


def _published_sort_key(post: dict[str, Any]) -> int:
    ts = _parse_ts(post.get("published_at"))
    if ts is not None:
        return int(ts.timestamp())
    idx = post.get("_index", 0)
    return -idx * 1000


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        if isinstance(value, int | float):
            return datetime.fromtimestamp(float(value), tz=UTC)
        s = str(value).strip()
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(s, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                return dt
            except ValueError:
                continue
    except Exception:
        pass
    return None


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
