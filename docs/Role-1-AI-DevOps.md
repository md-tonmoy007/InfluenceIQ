# Role 1: Platform + Orchestration

This role owns the runtime platform that keeps the API, workers, Redis, and database operating as one system.

## Mission

Provide a reliable execution environment for campaign orchestration, queue routing, worker isolation, state tracking, and deployment. This role owns how the pipeline runs, not how influencers are scored.

## Owns

- Docker and service composition for API, frontend, Redis, PostgreSQL, workers, and Flower
- Environment configuration in `backend/core/config.py` and runtime secrets handling
- Redis connectivity, cache primitives, pipeline state, and event replay storage in `backend/core/cache/`
- Celery app construction and task routing in `backend/core/celery/`
- Worker process topology in `backend/workers/ai_agent/`, `backend/workers/scraping/`, and `backend/workers/scoring/`
- Queue health, worker startup conventions, retry posture, logging, and deployment observability

## Interfaces Consumed

- Pipeline task names from `backend/pipeline/tasks/`
- API startup and runtime requirements from `backend/api/main.py`
- Database connectivity requirements from `backend/core/database/`

## Interfaces Produced

- Queue routing contract in `backend/core/celery/roles.py`
- Runtime queue set:
  - `ai_agent_queue`
  - `scraping_queue`
  - `scoring_queue`
- Redis state and replay primitives:
  - `pipeline_state:{campaign_id}`
  - `pipeline_events:{campaign_id}`
- Process and health topology for local dev and deployment

## Key Workflows

- Start the FastAPI app with access to PostgreSQL and Redis.
- Start the three worker roles with queue assignments that match `backend/core/celery/roles.py`.
- Ensure task adapters can update Redis state and append replayable events while pipeline jobs run.
- Keep Flower and service logs usable for diagnosing stuck queues, replay gaps, and retry storms.
- Preserve deterministic behavior when optional LLM or ML adapters are disabled or unavailable.

## Non-Goals

- Does not define recommendation formulas, brand-safety rules, or extraction heuristics.
- Does not own public REST response shape beyond health and runtime behavior.
- Does not duplicate pipeline-domain persistence logic that belongs in backend or pipeline code.

## Key Files And Directories

- `docker-compose.yml`
- `backend/core/config.py`
- `backend/core/celery/app.py`
- `backend/core/celery/factory.py`
- `backend/core/celery/roles.py`
- `backend/core/cache/redis_client.py`
- `backend/core/cache/pipeline_state.py`
- `backend/core/cache/event_log.py`
- `backend/workers/`
- `README.md`

## Handoff Contracts

- To Backend API + Data:
  - Redis and Celery must be reachable with stable configuration.
  - `pipeline_state` and `pipeline_events` behavior must match the API replay and polling assumptions.
- To Pipeline Intelligence:
  - Task routes and queue names must stay stable or be changed in lockstep with task producers/consumers.
  - Worker environments must expose the feature flags and credentials required by optional adapters.
- To Frontend:
  - Operational incidents should fail as partial or terminal campaign states instead of silent hangs.
