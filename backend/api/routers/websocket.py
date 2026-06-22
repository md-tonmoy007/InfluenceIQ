"""WebSocket replay + live pipeline event stream.

Connection contract
-------------------
``ws://<host>/ws/campaign/{campaign_id}?last_event_id=N``

1. Server accepts and replays every event for ``campaign_id`` with
   ``event_id > N`` (in order), then subscribes to the live pub/sub
   channel ``campaign:{campaign_id}``.
2. Heartbeat: server sends ``{"type": "ping", "timestamp": ...}``
   every ``HEARTBEAT_INTERVAL_SECONDS`` (20s by default).
3. The server also accepts client ``pong`` replies (and any other
   text frames) without taking action.
4. Slow-consumer policy: events are pushed into a bounded
   ``asyncio.Queue`` of size ``SEND_QUEUE_MAX`` (default 256). If the
   queue overflows, the server closes the WebSocket with code
   ``1008`` ("policy violation") and reason ``"slow consumer"``; the
   client can reconnect with the last received ``event_id`` to
   resume.
5. On any other error, the server unsubscribes from the channel,
   closes Redis connections, and closes the WebSocket.

Replay contract
---------------
``last_event_id`` is optional. When omitted, no replay happens and
the client only sees events emitted after the WebSocket connected.
When present, it must be a non-negative integer; an invalid value
yields ``1008`` with reason ``"invalid last_event_id"``.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from uuid import UUID

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from backend.core.cache.event_log import aget_event_replay
from backend.core.config import settings

logger = structlog.get_logger()
router = APIRouter(tags=["websocket"])

# Slow-consumer policy constants.
SEND_QUEUE_MAX = 256
HEARTBEAT_INTERVAL_SECONDS = 20

# Reasons sent as ``code=1008`` close frames. Keep these short and
# stable; clients can pattern-match on them.
CLOSE_REASON_SLOW_CONSUMER = "slow consumer"
CLOSE_REASON_INVALID_LAST_EVENT_ID = "invalid last_event_id"


# ---------------------------------------------------------------------------
# Subscriber registry — used by /api/metrics later and by tests.
# ---------------------------------------------------------------------------
class _SubscriberRegistry:
    """Track active WebSocket subscribers per campaign for metrics.

    Lightweight in-process registry; not shared across worker processes.
    The metrics path is best-effort: ``inc``/``dec`` swallow any
    KeyError so a stale removal can never crash the event loop.
    """

    def __init__(self) -> None:
        self._counts: dict[str, int] = defaultdict(int)

    def inc(self, campaign_id: str) -> int:
        self._counts[campaign_id] += 1
        return self._counts[campaign_id]

    def dec(self, campaign_id: str) -> int:
        current = self._counts.get(campaign_id, 0)
        if current <= 1:
            self._counts.pop(campaign_id, None)
            return 0
        self._counts[campaign_id] = current - 1
        return self._counts[campaign_id]

    def subscribers(self, campaign_id: str) -> int:
        return self._counts.get(campaign_id, 0)

    def total(self) -> int:
        return sum(self._counts.values())


SUBSCRIBERS = _SubscriberRegistry()


@router.websocket("/ws/campaign/{campaign_id}")
async def websocket_campaign_stream(
    websocket: WebSocket,
    campaign_id: UUID,
    last_event_id: int | None = Query(default=None, alias="last_event_id"),
):
    """Hardened pipeline event stream.

    See module docstring for the full protocol. The implementation is
    the canonical (and only) live-stream path used by the frontend.
    """
    campaign_id_str = str(campaign_id)
    log = logger.bind(campaign_id=campaign_id_str)

    # Validate last_event_id BEFORE accept() so a malformed cursor
    # surfaces as a protocol-level close instead of a half-opened
    # socket that immediately closes.
    if last_event_id is not None and last_event_id < 0:
        await websocket.close(code=1008, reason=CLOSE_REASON_INVALID_LAST_EVENT_ID)
        return

    await websocket.accept()
    log.info("WebSocket connection established")
    SUBSCRIBERS.inc(campaign_id_str)

    send_queue: asyncio.Queue = asyncio.Queue(maxsize=SEND_QUEUE_MAX)
    closed_due_to_overflow = False

    async def _enqueue_safely(event: dict) -> bool:
        """Push ``event`` to the queue. Returns False if overflow occurred."""
        try:
            send_queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            return False

    try:
        # ----------------------------------------------------------------
        # Step 1: Replay missed events
        # ----------------------------------------------------------------
        if last_event_id is not None:
            try:
                async_redis = aioredis.from_url(
                    settings.REDIS_URL, decode_responses=True
                )
                try:
                    missed_events = await aget_event_replay(
                        async_redis, campaign_id_str, last_event_id
                    )
                finally:
                    await async_redis.close()
                for event in missed_events:
                    if not await _enqueue_safely(event):
                        closed_due_to_overflow = True
                        break
                log.info(
                    "Replayed events successfully", count=len(missed_events)
                )
            except Exception as e:
                log.error("Failed to replay missed events", error=str(e))

        if closed_due_to_overflow:
            log.warning("Closing due to overflow during replay")
            await websocket.close(
                code=1008, reason=CLOSE_REASON_SLOW_CONSUMER
            )
            return

        # ----------------------------------------------------------------
        # Step 2: Subscribe to Redis pub/sub
        # ----------------------------------------------------------------
        pubsub_redis = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
        pubsub = pubsub_redis.pubsub()
        channel_name = f"campaign:{campaign_id_str}"

        try:
            await pubsub.subscribe(channel_name)
            log.info(
                "Subscribed to Redis pub/sub channel", channel=channel_name
            )

            # ----------------------------------------------------------------
            # Step 3: Sender task — drains the queue and forwards to client
            # ----------------------------------------------------------------
            sender_stop = asyncio.Event()

            async def sender_loop() -> None:
                while not sender_stop.is_set():
                    try:
                        event = await asyncio.wait_for(
                            send_queue.get(), timeout=1.0
                        )
                    except TimeoutError:
                        continue
                    try:
                        await websocket.send_json(event)
                    except (WebSocketDisconnect, asyncio.CancelledError):
                        break
                    except Exception as e:
                        log.warning(
                            "sender_loop send failed", error=str(e)
                        )
                        break

            async def send_heartbeat() -> None:
                while not sender_stop.is_set():
                    try:
                        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
                        heartbeat = {
                            "type": "ping",
                            "timestamp": asyncio.get_event_loop().time(),
                        }
                        await websocket.send_json(heartbeat)
                    except (WebSocketDisconnect, asyncio.CancelledError):
                        break
                    except Exception as e:
                        log.warning(
                            "Heartbeat send failed", error=str(e)
                        )
                        break

            async def stream_pubsub_events() -> None:
                while not sender_stop.is_set():
                    try:
                        message = await pubsub.get_message(
                            ignore_subscribe_messages=True, timeout=1.0
                        )
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        log.error(
                            "Redis pub/sub get_message error", error=str(e)
                        )
                        continue
                    if not message or message.get("type") != "message":
                        continue
                    data_str = message.get("data")
                    if not data_str:
                        continue
                    try:
                        event_data = json.loads(data_str)
                    except json.JSONDecodeError:
                        log.warning(
                            "Received invalid JSON from Redis channel",
                            raw_data=data_str,
                        )
                        continue
                    if not await _enqueue_safely(event_data):
                        # Slow consumer. Signal the other tasks to stop
                        # and let the outer try/finally close the socket
                        # with code 1008.
                        log.warning(
                            "Send queue overflow — closing as slow consumer",
                            queue_max=SEND_QUEUE_MAX,
                        )
                        sender_stop.set()
                        # Schedule the close from the sender loop so we
                        # don't race the outer finally block.
                        asyncio.create_task(
                            websocket.close(
                                code=1008,
                                reason=CLOSE_REASON_SLOW_CONSUMER,
                            )
                        )
                        return

            async def read_client_messages() -> None:
                while not sender_stop.is_set():
                    try:
                        data = await websocket.receive_text()
                    except WebSocketDisconnect:
                        log.info("Client initiated WebSocket disconnect")
                        sender_stop.set()
                        return
                    except asyncio.CancelledError:
                        return
                    except Exception as e:
                        log.warning(
                            "Error reading client messages", error=str(e)
                        )
                        sender_stop.set()
                        return
                    try:
                        parsed = json.loads(data)
                        if parsed.get("type") == "pong":
                            log.debug("Received pong from client")
                    except Exception:
                        pass

            sender_task = asyncio.create_task(sender_loop())
            heartbeat_task = asyncio.create_task(send_heartbeat())
            stream_task = asyncio.create_task(stream_pubsub_events())
            client_task = asyncio.create_task(read_client_messages())

            try:
                await sender_stop.wait()
            finally:
                # Cancel every coroutine we started so the await below
                # doesn't leak tasks.
                for task in (
                    sender_task,
                    heartbeat_task,
                    stream_task,
                    client_task,
                ):
                    task.cancel()
                # Drain cancellations.
                for task in (
                    sender_task,
                    heartbeat_task,
                    stream_task,
                    client_task,
                ):
                    try:
                        await task
                    except (asyncio.CancelledError, Exception):
                        pass

        except WebSocketDisconnect:
            log.info("WebSocket disconnected during subscription")
        except Exception as e:
            log.error("WebSocket controller error occurred", error=str(e))
        finally:
            try:
                await pubsub.unsubscribe(channel_name)
                await pubsub.close()
                await pubsub_redis.close()
            except Exception as e:
                log.error("Error during Redis pub/sub cleanup", error=str(e))

    except WebSocketDisconnect:
        log.info("WebSocket disconnected during replay")
    except Exception as e:
        log.error("WebSocket controller error occurred (outer)", error=str(e))
    finally:
        SUBSCRIBERS.dec(campaign_id_str)
        try:
            await websocket.close()
        except Exception:
            pass


__all__ = [
    "CLOSE_REASON_INVALID_LAST_EVENT_ID",
    "CLOSE_REASON_SLOW_CONSUMER",
    "HEARTBEAT_INTERVAL_SECONDS",
    "SEND_QUEUE_MAX",
    "SUBSCRIBERS",
]
