"""Manual smoke test for the YouTube provider.

Runs ``fetch_youtube_profile`` against a real handle and prints the
result. Does NOT make assertions — just a quick eyeball check.

Usage:
    uv run --directory backend python scripts/test_youtube.py [@handle]

Default handle: ``@mkbhd``
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.config import settings  # noqa: E402
from backend.pipeline.content.cache import clear_youtube_api_cache  # noqa: E402
from backend.pipeline.content.providers.youtube import fetch_youtube_profile  # noqa: E402


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    handle = args[0] if args else "@mkbhd"
    url = f"https://www.youtube.com/{handle}" if not handle.startswith("http") else handle

    print(f"YOUTUBE_API_KEY set: {bool(settings.YOUTUBE_API_KEY)}")
    print(f"length: {len(settings.YOUTUBE_API_KEY)}")
    print(f"URL: {url}")
    if "--no-cache" in flags:
        print("Clearing YouTube API cache...")
        deleted = clear_youtube_api_cache()
        print(f"  cleared {deleted} cached entries")
    print()

    print("Fetching profile (this may take a few seconds)...\n")
    profile = fetch_youtube_profile(url)

    if profile is None:
        print("ERROR: profile is None")
        sys.exit(1)

    print(f"provider:        {profile.provider}")
    print(f"handle:          {profile.handle}")
    print(f"name:            {profile.name}")
    print(f"followers:       {profile.followers:,}" if profile.followers else "followers:       None")
    print(f"verified:        {profile.verified}")
    print(f"posts returned:  {len(profile.posts)}")
    print(f"error:           {profile.error}")
    print(f"channel_id:      {profile.raw.get('channel_id')}")
    print(f"lifetime_views:  {profile.raw.get('lifetime_views'):,}" if profile.raw.get("lifetime_views") else "lifetime_views:  None")
    print(f"video_count:     {profile.raw.get('video_count')}")
    print(f"api_source:      {profile.raw.get('api_source')}")
    print()
    if profile.posts:
        print("First 3 posts (id, view_count, like_count, comment_count):")
        for p in profile.posts[:3]:
            print(f"  {p.get('id')}: views={p.get('view_count')} likes={p.get('like_count')} comments={p.get('comment_count')}")
            print(f"    title: {p.get('title')[:60]}")


if __name__ == "__main__":
    main()
