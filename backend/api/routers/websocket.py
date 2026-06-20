from __future__ import annotations

import asyncio
import json
from uuid import UUID

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from backend.core.cache.event_log import aget_event_replay
from backend.core.config import settings

logger = structlog.get_logger()
router = APIRouter(tags=["websocket"])

@router.websocket("/ws/campaign/{campaign_id}")
async def websocket_campaign_stream(
    websocket: WebSocket,
    campaign_id: UUID,
    last_event_id: int | None = Query(default=None, alias="last_event_id"),
):
    """
    WebSocket endpoint at /ws/campaign/{campaign_id}
    - Accepts WebSocket connection.
    - Replays missed events if last_event_id is specified.
    - Subscribes to Redis channel campaign:{campaign_id} for real-time streaming.
    - Features a 20-second active ping-pong heartbeat.
    - Handles graceful connection teardown to avoid resource leaks.
    """
    campaign_id_str = str(campaign_id)
    log = logger.bind(campaign_id=campaign_id_str)

    await websocket.accept()
    log.info("WebSocket connection established")

    # Step 1: Replay missed events if requested
    if last_event_id is not None:
        try:
            log.info("Replaying events", last_event_id=last_event_id)
            async_redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            try:
                missed_events = await aget_event_replay(async_redis, campaign_id_str, last_event_id)
            finally:
                await async_redis.close()
            for event in missed_events:
                await websocket.send_json(event)
            log.info("Replayed events successfully", count=len(missed_events))
        except Exception as e:
            log.error("Failed to replay missed events", error=str(e))
            # Continue connection despite replay failure to preserve service availability

    # Step 2: Establish Redis pub/sub subscription
    pubsub_redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = pubsub_redis.pubsub()
    channel_name = f"campaign:{campaign_id_str}"

    try:
        await pubsub.subscribe(channel_name)
        log.info("Subscribed to Redis pub/sub channel", channel=channel_name)

        # We run the ping/pong heartbeat and the pub/sub listener concurrently
        # We need a shared flag to communicate disconnection
        is_active = True

        async def send_heartbeat():
            nonlocal is_active
            while is_active:
                try:
                    await asyncio.sleep(20)
                    log.debug("Sending heartbeat ping")
                    # Send a text ping frame to keep connection alive
                    await websocket.send_json({"type": "ping", "timestamp": asyncio.get_event_loop().time()})
                except (WebSocketDisconnect, asyncio.CancelledError):
                    break
                except Exception as e:
                    log.warning("Heartbeat send failed", error=str(e))
                    break

        async def stream_pubsub_events():
            nonlocal is_active
            try:
                while is_active:
                    # Non-blocking get_message to allow task cancellation or heartbeat interruption
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message.get("type") == "message":
                        data_str = message.get("data")
                        if data_str:
                            try:
                                event_data = json.loads(data_str)
                                await websocket.send_json(event_data)
                                log.info("Forwarded event to WebSocket client", event_type=event_data.get("type"))
                            except json.JSONDecodeError:
                                log.warning("Received invalid JSON from Redis channel", raw_data=data_str)
                            except Exception as e:
                                log.error("Failed to send event to client", error=str(e))
                                break
            except asyncio.CancelledError:
                pass
            except Exception as e:
                log.error("Redis pub/sub stream error occurred", error=str(e))

        # Run listener and heartbeat concurrently
        heartbeat_task = asyncio.create_task(send_heartbeat())
        stream_task = asyncio.create_task(stream_pubsub_events())

        # Also wait for any client message (which signals disconnect or unexpected client uploads)
        async def read_client_messages():
            nonlocal is_active
            try:
                while is_active:
                    # Wait for message from client (e.g. client sending pong)
                    data = await websocket.receive_text()
                    try:
                        parsed = json.loads(data)
                        if parsed.get("type") == "pong":
                            log.debug("Received pong from client")
                    except Exception:
                        pass
            except WebSocketDisconnect:
                log.info("Client initiated WebSocket disconnect")
            except Exception as e:
                log.warning("Error reading client messages", error=str(e))
            finally:
                is_active = False

        client_task = asyncio.create_task(read_client_messages())

        # Wait until any task completes (most likely client_task on disconnect)
        done, pending = await asyncio.wait(
            [heartbeat_task, stream_task, client_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel all pending tasks to prevent resource leaks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except WebSocketDisconnect:
        log.info("WebSocket disconnected during subscription")
    except Exception as e:
        log.error("WebSocket controller error occurred", error=str(e))
    finally:
        # Step 3: Cleanup resources to prevent memory leaks
        log.info("Cleaning up WebSocket session resources")
        is_active = False

        # Unsubscribe and close Redis connections
        try:
            await pubsub.unsubscribe(channel_name)
            await pubsub.close()
            await pubsub_redis.close()
            log.info("Successfully unsubscribed and closed Redis connection")
        except Exception as e:
            log.error("Error during Redis pub/sub cleanup", error=str(e))

        # Close WebSocket if it is still open
        try:
            await websocket.close()
        except Exception:
            pass
