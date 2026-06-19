from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_PAYLOAD = {
    "brand": "Acme Health",
    "product": "Daily Greens",
    "category": "Wellness",
    "goal": "Find brand-safe wellness creators",
    "platforms": ["instagram", "youtube"],
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
    parser = argparse.ArgumentParser(description="Run an end-to-end InfluenceIQ campaign smoke test.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    try:
        health = request_json("GET", f"{base_url}/health")
        print(f"health.status={health.get('status')} db={health.get('db')} redis={health.get('redis')}")

        created = request_json("POST", f"{base_url}/api/campaigns", DEFAULT_PAYLOAD)
        campaign_id = created["campaign_id"]
        print(f"campaign_id={campaign_id}")

        deadline = time.monotonic() + args.timeout
        state: dict[str, Any] = {}
        while time.monotonic() < deadline:
            state = request_json("GET", f"{base_url}/api/campaigns/{campaign_id}/state")
            status = state.get("status")
            phase = state.get("phase")
            print(f"state.status={status} phase={phase}")
            if status in {"completed", "failed"}:
                break
            time.sleep(args.interval)

        if state.get("status") != "completed":
            print(f"Smoke test failed: campaign did not complete. Last state: {state}", file=sys.stderr)
            return 1

        influencers = request_json("GET", f"{base_url}/api/campaigns/{campaign_id}/influencers")
        items = influencers.get("items", [])
        if not items:
            print("Smoke test failed: campaign completed with no influencers.", file=sys.stderr)
            return 1

        print(f"smoke.ok campaign_id={campaign_id} influencers={len(items)}")
        return 0
    except (HTTPError, URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
