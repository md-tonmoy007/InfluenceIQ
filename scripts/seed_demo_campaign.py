from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEMO_PAYLOAD = {
    "brand": "Northwind Outdoor",
    "product": "SS26 Trail Capsule",
    "category": "Outdoor & Activewear",
    "goal": "Product Launch",
    "ages": ["18-24", "25-34"],
    "gender": "All",
    "locations": ["USA", "Canada"],
    "platforms": ["instagram", "youtube"],
    "tier": "Established",
    "budget": "$2,500 - $12,000 USD",
}


def request_json(method: str, url: str, payload: dict[str, Any] | None = None) -> Any:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a demo campaign and wait for shortlist completion.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    try:
        created = request_json("POST", f"{base_url}/api/campaigns", DEMO_PAYLOAD)
        campaign_id = created["campaign_id"]
        print(f"seeded campaign_id={campaign_id}")

        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            state = request_json("GET", f"{base_url}/api/campaigns/{campaign_id}/state")
            print(
                f"state.status={state.get('status')} phase={state.get('phase')} influencers={state.get('influencer_count', 0)}"
            )
            if state.get("status") == "completed":
                shortlist = request_json("GET", f"{base_url}/api/campaigns/{campaign_id}/influencers")
                print(
                    f"demo.ready campaign_id={campaign_id} influencers={len(shortlist.get('items', []))}"
                )
                return 0
            if state.get("status") == "failed":
                print(f"Demo seed failed: {state}", file=sys.stderr)
                return 1
            time.sleep(args.interval)

        print("Demo seed timed out before completion.", file=sys.stderr)
        return 1
    except (HTTPError, URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
        print(f"Demo seed failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
