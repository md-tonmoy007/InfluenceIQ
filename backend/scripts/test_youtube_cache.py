"""Debug: verify cache keys and contents."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.config import settings  # noqa: E402
from backend.pipeline.content.cache import (  # noqa: E402
    YOUTUBE_API_CACHE_PREFIX,
    redis_client,
)


def main() -> None:
    print(f"YOUTUBE_API_KEY: {bool(settings.YOUTUBE_API_KEY)}")
    print()
    print("Cache keys matching youtube_api prefix:")
    try:
        client = redis_client()
        for key in client.scan_iter(match=f"{YOUTUBE_API_CACHE_PREFIX}*"):
            ttl = client.ttl(key)
            raw = client.get(key)
            val = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            preview = (val or "")[:120]
            print(f"  {key.decode() if isinstance(key, bytes) else key}")
            print(f"    ttl={ttl}s  value={preview}...")
    except Exception as exc:
        print(f"  ERROR: {exc!r}")


if __name__ == "__main__":
    main()
