# Role 3: Backend API + Data

This role owns the public API surface and the durable data model that the rest of the system depends on.

## Mission

Provide stable FastAPI contracts, durable PostgreSQL persistence, campaign state read surfaces, and WebSocket replay behavior that expose pipeline work safely to clients.

## Owns

- FastAPI app composition in `backend/api/main.py`
- HTTP route handlers in `backend/api/routers/`
- Request and response schemas in `backend/api/schemas/`
- SQLAlchemy models, sessions, and migrations in `backend/core/database/`
- Database-backed campaign, influencer, source, and score persistence contracts
- WebSocket replay surface and client stream attachment in `backend/api/routers/websocket.py`

## Interfaces Consumed

- Redis pipeline state and replay log from `backend/core/cache/`
- Queue-dispatched pipeline work started through `backend.pipeline.tasks`
- Pipeline outputs persisted through shared database models

## Interfaces Produced

- `POST /api/campaigns`
- `GET /api/campaigns/{id}`
- `GET /api/campaigns/{id}/state`
- `GET /api/campaigns/{id}/influencers`
- `GET /api/influencers/{id}`
- `/ws/campaign/{campaign_id}?last_event_id=N`
- Durable tables such as campaigns, influencers, crawl sources, and influencer scores

## Key Workflows

- Create a campaign row, initialize Redis pipeline state, and dispatch pipeline execution.
- Translate database models and Redis state into public REST payloads.
- Replay missed events from `pipeline_events:{campaign_id}` before attaching the WebSocket client to the live stream.
- Expose ranked campaign recommendations with score and provenance data attached.
- Expose canonical influencer profiles without leaking pipeline-internal implementation details into the public contract.

## Non-Goals

- Does not own search-provider behavior, extraction heuristics, or scoring policy.
- Does not own queue topology or worker scaling strategy.
- Does not duplicate pipeline-domain reasoning inside route handlers unless needed for contract translation.

## Key Files And Directories

- `backend/api/main.py`
- `backend/api/routers/campaigns.py`
- `backend/api/routers/influencers.py`
- `backend/api/routers/websocket.py`
- `backend/api/routers/health.py`
- `backend/api/schemas/`
- `backend/core/database/models.py`
- `backend/core/database/session.py`
- `backend/core/database/migrations/`

## Handoff Contracts

- From Platform + Orchestration:
  - Redis and Celery contracts must support campaign initialization, state reads, and event replay.
- From Pipeline Intelligence:
  - Persisted score outputs must include enough provenance and explanation data to satisfy API consumers.
  - Event payloads must fit the public event envelope and remain safe for replay.
- To Frontend:
  - Partial campaigns, failures, and completed campaigns must all return explicit lifecycle states.
  - The same event shape must be used for replayed and live WebSocket delivery.
