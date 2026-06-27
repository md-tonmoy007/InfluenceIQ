from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_PAYLOAD = {
    "product": "Daily Greens",
    "industry": "Wellness",
    "goals": "Find brand-safe wellness creators",
    "preferred_platforms": ["instagram", "youtube"],
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


def poll_campaign_completion(campaign_id: str, deadline: float, interval: float) -> dict[str, Any]:
    """Poll until the campaign reaches a terminal DB status."""
    from backend.pipeline.tasks._common import db_session, get_campaign, refresh_campaign_status

    state: dict[str, Any] = {"status": "unknown", "phase": "unknown"}
    while time.monotonic() < deadline:
        with db_session() as session:
            refresh_campaign_status(session, campaign_id)
            campaign = get_campaign(session, campaign_id)
            status = campaign.status
            phase = campaign.status or "unknown"
        state = {"status": status, "phase": phase}
        print(f"state.status={status} phase={phase}")
        if status in {"completed", "failed", "partial"}:
            return state
        time.sleep(interval)
    return state


def count_scored_influencers(campaign_id: str) -> int:
    from uuid import UUID

    from backend.core.database import models
    from backend.pipeline.tasks._common import db_session

    with db_session() as session:
        return (
            session.query(models.InfluencerScore.influencer_id)
            .filter(models.InfluencerScore.campaign_id == UUID(campaign_id))
            .distinct()
            .count()
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an end-to-end InfluenceIQ campaign smoke test.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    try:
        health = request_json("GET", f"{base_url}/health")
        print(f"health.status={health.get('status')} db={health.get('db')} redis={health.get('redis')}")

        created = request_json("POST", f"{base_url}/api/campaigns", DEFAULT_PAYLOAD)
        campaign_id = created["campaign_id"]
        print(f"campaign_id={campaign_id}")

        state = poll_campaign_completion(
            campaign_id,
            time.monotonic() + args.timeout,
            args.interval,
        )

        if state.get("status") not in {"completed", "partial"}:
            print(f"Smoke test failed: campaign did not complete. Last state: {state}", file=sys.stderr)
            return 1

        influencer_count = count_scored_influencers(campaign_id)
        if influencer_count == 0:
            print("Smoke test failed: campaign completed with no influencers.", file=sys.stderr)
            return 1

        print(f"smoke.ok campaign_id={campaign_id} influencers={influencer_count}")
        return 0
    except (HTTPError, URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
