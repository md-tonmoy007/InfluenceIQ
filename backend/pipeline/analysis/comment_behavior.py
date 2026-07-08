"""Behavioral feature extraction from real audience comments.

Turns post timestamps + comment authors/timestamps/text into the feature
keys that :func:`score_bot_behavior` and :func:`score_coordinated_engagement`
already consume.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime
from itertools import combinations
from typing import Any

from backend.pipeline.analysis.fake_comment import _normalized


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _uniformity_score(gaps: list[float]) -> float:
    """Return 1 − normalized coefficient of variation, clamped to [0, 1].

    A perfectly uniform sequence scores 1; highly irregular sequences score
    near 0. Requires at least two gaps.
    """
    if len(gaps) < 2:
        return 0.0
    mean = sum(gaps) / len(gaps)
    if mean == 0:
        return 0.0
    variance = sum((g - mean) ** 2 for g in gaps) / len(gaps)
    cv = variance**0.5 / mean
    # Normalise so cv >= 1 maps to 0 and cv == 0 maps to 1.
    return max(0.0, min(1.0, 1.0 - cv))


def _night_hour(dt: datetime | None) -> bool:
    if dt is None:
        return False
    return 2 <= dt.hour < 5


def extract_behavior_features(
    posts: list[dict[str, Any]],
    comments: list[dict[str, Any]],
) -> dict[str, float]:
    """Compute bot/coordination features from posts and comments.

    ``posts`` entries should contain ``external_id`` and ``published_at``.
    ``comments`` entries should contain ``post_external_id``, ``author_hash``,
    ``text``, and ``published_at``.

    Returns an empty dict when there are fewer than 30 timestamped comments,
    preserving the current "absent features → 0 risk" semantics.
    """
    timestamped_comments = [
        c for c in comments
        if _parse_dt(c.get("published_at")) is not None
    ]
    if len(timestamped_comments) < 30:
        return {}

    post_times = sorted(
        {p["external_id"]: _parse_dt(p.get("published_at")) for p in posts if _parse_dt(p.get("published_at")) is not None}.items(),
        key=lambda x: x[1],
    )

    comments_by_post: dict[str, list[dict]] = defaultdict(list)
    authors_by_post: dict[str, set[str]] = defaultdict(set)
    for comment in comments:
        post_id = str(comment.get("post_external_id") or "")
        if not post_id:
            continue
        comments_by_post[post_id].append(comment)
        author = str(comment.get("author_hash") or "")
        if author:
            authors_by_post[post_id].add(author)

    # posting_interval_uniformity
    posting_interval_uniformity = 0.0
    if len(post_times) >= 4:
        gaps = [
            (post_times[i + 1][1] - post_times[i][1]).total_seconds() / 60.0
            for i in range(len(post_times) - 1)
        ]
        posting_interval_uniformity = _uniformity_score(gaps)

    # comment_interval_uniformity (averaged per post)
    comment_uniformity_values: list[float] = []
    for _post_id, post_comments in comments_by_post.items():
        times = sorted(_parse_dt(c.get("published_at")) for c in post_comments if _parse_dt(c.get("published_at")) is not None)
        if len(times) >= 5:
            gaps = [(times[i + 1] - times[i]).total_seconds() / 60.0 for i in range(len(times) - 1)]
            comment_uniformity_values.append(_uniformity_score(gaps))
    comment_interval_uniformity = (
        sum(comment_uniformity_values) / len(comment_uniformity_values)
        if comment_uniformity_values else 0.0
    )

    # same_text_reuse_ratio
    text_to_posts: dict[str, set[str]] = defaultdict(set)
    text_to_authors: dict[str, set[str]] = defaultdict(set)
    for comment in comments:
        text = _normalized(str(comment.get("text", "")))
        if not text:
            continue
        post_id = str(comment.get("post_external_id") or "")
        text_to_posts[text].add(post_id)
        author = str(comment.get("author_hash") or "")
        if author:
            text_to_authors[text].add(author)

    total_texts = len(text_to_posts)
    reused_across_posts = sum(1 for posts_set in text_to_posts.values() if len(posts_set) >= 2)
    same_text_reuse_ratio = reused_across_posts / total_texts if total_texts else 0.0

    # engagement_burst_score
    burst_scores: list[float] = []
    for post_comments in comments_by_post.values():
        times = sorted(_parse_dt(c.get("published_at")) for c in post_comments if _parse_dt(c.get("published_at")) is not None)
        if len(times) < 2:
            continue
        best = 1
        for _i, start in enumerate(times):
            window_end = start.timestamp() + 600  # 10 minutes
            count = sum(1 for t in times if start.timestamp() <= t.timestamp() <= window_end)
            if count > best:
                best = count
        burst_scores.append(best / len(times))
    engagement_burst_score = sum(burst_scores) / len(burst_scores) if burst_scores else 0.0

    # night_activity_ratio
    night_count = sum(1 for c in timestamped_comments if _night_hour(_parse_dt(c.get("published_at"))))
    night_activity_ratio = night_count / len(timestamped_comments)

    # activity_velocity_score (posts per day over sampled window)
    activity_velocity_score = 0.0
    if len(post_times) >= 2:
        window_days = max(1.0, (post_times[-1][1] - post_times[0][1]).total_seconds() / 86400.0)
        posts_per_day = len(post_times) / window_days
        activity_velocity_score = min(1.0, posts_per_day / 3.0)

    # repeated_commenter_cluster_score
    author_post_counts: Counter = Counter()
    for _post_id, authors in authors_by_post.items():
        for author in authors:
            author_post_counts[author] += 1
    total_authors = len(author_post_counts)
    repeated_authors = sum(1 for count in author_post_counts.values() if count >= 3)
    repeated_commenter_cluster_score = (
        repeated_authors / total_authors if total_authors >= 20 else 0.0
    )

    # duplicate_text_cluster_score
    duplicated_texts = sum(
        1 for text, authors in text_to_authors.items()
        if len(authors) >= 3
    )
    duplicate_text_cluster_score = duplicated_texts / total_texts if total_texts else 0.0

    # synchronized_activity_score
    author_post_times: dict[str, list[tuple[str, datetime]]] = defaultdict(list)
    for comment in comments:
        author = str(comment.get("author_hash") or "")
        post_id = str(comment.get("post_external_id") or "")
        dt = _parse_dt(comment.get("published_at"))
        if author and post_id and dt:
            author_post_times[author].append((post_id, dt))

    pair_matches: set[tuple[str, str]] = set()
    authors = list(author_post_times.keys())
    # Cap pair scan to keep runtime bounded.
    max_authors = 200
    if len(authors) > max_authors:
        authors = authors[:max_authors]
    for a, b in combinations(authors, 2):
        a_posts = {(p, t) for p, t in author_post_times[a]}
        b_events = author_post_times[b]
        co_post_count = 0
        for post_a, time_a in a_posts:
            for post_b, time_b in b_events:
                if post_a != post_b and abs((time_a - time_b).total_seconds()) <= 300:
                    co_post_count += 1
                    break
        if co_post_count >= 2:
            pair_matches.add(tuple(sorted((a, b))))

    total_pairs = max(1, len(authors) * (len(authors) - 1) // 2)
    synchronized_activity_score = len(pair_matches) / total_pairs

    # shared_hashtag_cluster_score
    hashtag_to_authors: dict[str, set[str]] = defaultdict(set)
    for comment in comments:
        text = str(comment.get("text", ""))
        author = str(comment.get("author_hash") or "")
        for tag in re.findall(r"#(\w+)", text):
            if author:
                hashtag_to_authors[tag.lower()].add(author)
    total_comments_with_hashtags = sum(
        1 for c in comments if re.search(r"#\w+", str(c.get("text", "")))
    )
    shared_hashtag_comments = sum(
        1 for c in comments
        if any(
            len(hashtag_to_authors[tag.lower()]) >= 3
            for tag in re.findall(r"#(\w+)", str(c.get("text", "")))
        )
    )
    shared_hashtag_cluster_score = (
        shared_hashtag_comments / total_comments_with_hashtags
        if total_comments_with_hashtags else 0.0
    )

    return {
        "posting_interval_uniformity": round(posting_interval_uniformity, 4),
        "comment_interval_uniformity": round(comment_interval_uniformity, 4),
        "same_text_reuse_ratio": round(same_text_reuse_ratio, 4),
        "engagement_burst_score": round(engagement_burst_score, 4),
        "night_activity_ratio": round(night_activity_ratio, 4),
        "activity_velocity_score": round(activity_velocity_score, 4),
        "repeated_commenter_cluster_score": round(repeated_commenter_cluster_score, 4),
        "duplicate_text_cluster_score": round(duplicate_text_cluster_score, 4),
        "synchronized_activity_score": round(synchronized_activity_score, 4),
        "shared_hashtag_cluster_score": round(shared_hashtag_cluster_score, 4),
    }
