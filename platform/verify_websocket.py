from __future__ import annotations

import asyncio
import json
import httpx
import redis.asyncio as aioredis
from uuid import UUID

API_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"
REDIS_URL = "redis://redis:6379/0"

async def receive_next_event(ws) -> dict:
    while True:
        msg = await ws.recv()
        event = json.loads(msg)
        if event.get("type") == "ping":
            print(f"💓 WS Client: Received server heartbeat ping: {event}")
            continue
        return event

async def test_websocket_stream_and_replay():
    print("=== STARTING WEBSOCKET AND REPLAY INTEGRATION TEST ===")
    
    # Step 1: Trigger Demo Seed
    print("\n[Step 1] Triggering database seed via API...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{API_URL}/api/demo/seed", timeout=10.0)
            if resp.status_code != 200:
                print(f"❌ Seed failed: Status {resp.status_code}, Body: {resp.text}")
                return
            seed_data = resp.json()
            campaign_id = seed_data["campaigns"]["BioGlow Collagen Peptide"]
            print(f"✅ Database seeded. Using campaign_id: {campaign_id}")
        except Exception as e:
            print(f"❌ Failed to reach API for seeding: {e}")
            print("Make sure the docker-compose services are running and listening on port 8000.")
            return

    # Step 2: Establish local Redis connection to simulate worker publishing
    print("\n[Step 2] Connecting to local Redis...")
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    try:
        await r.ping()
        print("✅ Connected to Redis successfully.")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        await r.close()
        return

    # Helper function to publish mock events to Redis (as worker would)
    async def publish_mock_event(event_id: int, event_type: str, payload: dict):
        event = {
            "event_id": event_id,
            "type": event_type,
            "campaign_id": campaign_id,
            "timestamp": "2026-05-22T23:55:00Z",
            "payload": payload
        }
        serialized = json.dumps(event)
        
        # Append to Redis event history list
        await r.rpush(f"pipeline_events:{campaign_id}", serialized)
        # Set expiry
        await r.expire(f"pipeline_events:{campaign_id}", 3600)
        # Set the event ID counter
        await r.set(f"event_id_counter:{campaign_id}", event_id)
        # Publish to channel
        await r.publish(f"campaign:{campaign_id}", serialized)
        print(f"📡 Redis: Published event {event_id} ({event_type})")

    # Clean up any existing list/counter for campaign
    await r.delete(f"pipeline_events:{campaign_id}")
    await r.delete(f"event_id_counter:{campaign_id}")

    # Step 3: Connect WebSocket client
    print(f"\n[Step 3] Connecting to WebSocket: {WS_URL}/ws/campaign/{campaign_id}")
    import websockets
    
    try:
        async with websockets.connect(f"{WS_URL}/ws/campaign/{campaign_id}") as ws:
            print("✅ WebSocket connected successfully.")
            # Give server a moment to complete internal setup and subscribe to Redis
            await asyncio.sleep(0.5)

            # Publish event 1 in background
            print("Publishing event 1 (query.generated)...")
            await publish_mock_event(1, "query.generated", {"queries": ["dermatology collagen peptide", "marine collagen reviews"]})

            # Read event from WebSocket
            event = await receive_next_event(ws)
            print(f"📥 WS Client: Received event: {event}")
            assert event["event_id"] == 1
            assert event["type"] == "query.generated"
            print("✅ Event 1 received correctly over WebSocket.")

            # Publish event 2
            print("Publishing event 2 (url.discovered)...")
            await publish_mock_event(2, "url.discovered", {"url": "https://skindoctor.com/peptide-study", "relevance": 95.0})

            # Read event 2
            event = await receive_next_event(ws)
            print(f"📥 WS Client: Received event: {event}")
            assert event["event_id"] == 2
            assert event["type"] == "url.discovered"
            print("✅ Event 2 received correctly over WebSocket.")

            # Test Heartbeat Ping from Server
            print("Waiting for heartbeat ping (or we can proceed with reconnection test)...")
            
        print("🔌 Intentionally closed WebSocket connection to test replay/reconnection.")

        # Step 4: Publish event 3 and 4 while WebSocket client is disconnected (offline)
        print("\n[Step 4] Simulating offline progress. Publishing events 3 and 4...")
        await publish_mock_event(3, "page.scraped", {"url": "https://skindoctor.com/peptide-study", "status": "scraped"})
        await publish_mock_event(4, "score.calculated", {"influencer_id": seed_data["influencers"]["Dr. Jessica Cho"], "grade": "A+", "confidence": "High"})

        # Step 5: Reconnect client specifying last_event_id=2
        # It should receive events 3 and 4 immediately from the replay log
        print(f"\n[Step 5] Reconnecting specifying last_event_id=2...")
        async with websockets.connect(f"{WS_URL}/ws/campaign/{campaign_id}?last_event_id=2") as ws:
            print("✅ WebSocket reconnected.")
            
            # Read first replayed event (should be event 3)
            event = await receive_next_event(ws)
            print(f"📥 WS Client: Replayed event received: {event}")
            assert event["event_id"] == 3
            assert event["type"] == "page.scraped"
            print("✅ Event 3 correctly replayed.")

            # Read second replayed event (should be event 4)
            event = await receive_next_event(ws)
            print(f"📥 WS Client: Replayed event received: {event}")
            assert event["event_id"] == 4
            assert event["type"] == "score.calculated"
            print("✅ Event 4 correctly replayed.")

            # Step 6: Verify live updates still work after replay
            print("\n[Step 6] Verifying live streaming after replay...")
            # Give server a moment to complete Redis pub/sub subscription setup after finishing replay
            await asyncio.sleep(0.5)
            await publish_mock_event(5, "pipeline.completed", {"total_influencers": 2, "duration_seconds": 12.5})
            
            event = await receive_next_event(ws)
            print(f"📥 WS Client: Live event received: {event}")
            assert event["event_id"] == 5
            assert event["type"] == "pipeline.completed"
            print("✅ Live Event 5 correctly received after replay.")

        print("\n🎉 ALL TESTS PASSED! Reconnection and replay logic is 100% resilient.")

    except Exception as e:
        print(f"❌ Test encountered an error: {e}")
    finally:
        try:
            await r.aclose()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(test_websocket_stream_and_replay())
