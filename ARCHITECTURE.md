# InfluenceIQ — Architecture

> A trust-aware influencer discovery platform. Brands submit a
> campaign; the system discovers candidate influencers via web
> search, crawls and extracts structured content, then scores
> each candidate for credibility, engagement quality, brand
> safety, sentiment, and source confidence. The dashboard shows
> the ranked list with explainable reasons.
>
> This document is the source of truth for the runtime topology,
> the data flow, the optional ML backends, and the developer
> recipes. The per-role deep dives live in `Docs/`.

## Runtime topology

```text
┌──────────────────────────────────────────────────────────────────────┐
│                       docker-compose cluster                        │
│                                                                      │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌──────────┐  │
│  │  frontend  │───▶│backend-core│───▶│  postgres  │    │  qdrant  │  │
│  │  (Next.js) │    │  (FastAPI) │    │            │    │  (opt.)  │  │
│  └────────────┘    └─────┬──────┘    └────────────┘    └──────────┘  │
│         ▲                │            ▲                              │
│         │  WS            ▼            │                              │
│         │       ┌───────────────┐     │                              │
│         │       │   redis       │◀────┘                              │
│         │       │  (broker +    │                                    │
│         │       │  state +      │                                    │
│         │       │  pub/sub)     │                                    │
│         │       └──────┬────────┘                                    │
│         │              │                                             │
│         │              ▼                                             │
│         │  ┌──────────────────────┐  ┌──────────────────────┐        │
│         │  │  worker_ai_agent     │  │  worker_scoring      │        │
│         │  │  -Q ai_agent_queue   │  │  -Q scoring_queue    │        │
│         │  │  -c 2                │  │  -c 4                │        │
│         │  └──────────────────────┘  └──────────────────────┘        │
│         │                                                              │
│         │  ┌──────────────────────┐  ┌──────────────────────┐        │
│         │  │  worker_scraping     │  │  flower              │        │
│         │  │  -Q scraping_queue   │  │  (UI on :5555)      │        │
│         │  │  -c 8                │  │                      │        │
│         │  └──────────────────────┘  └──────────────────────┘        │
│         │                                                              │
└─────────┼──────────────────────────────────────────────────────────────┘
          │  WebSocket
          ▼
   browser dashboard
```

The API + workers + Flower all share the same Docker image (built
from the repo-root `Dockerfile`). The image contains the `app/`
package, the worker shims, the `scoring_service/` and
`scraping_service/` domain code, and the optional `umgl_ai/`
package. `PYTHONPATH=/workspace` is the only environment variable
the workers need.

## Data flow: a single campaign

```text
POST /api/campaigns
  │
  │ 1. Create Campaign row in Postgres
  │ 2. initialize_pipeline_state(campaign_id) in Redis
  │ 3. start_pipeline(campaign_id).delay()
  ▼
ai_agent_queue   ── app.tasks.search.generate_queries
                    • Reads campaign fields
                    • Builds 3-5 deterministic queries
                    • Emits query.generation.completed
                    • Dispatches execute_search per query
                    │
                    ▼
scraping_queue   ── app.tasks.search.execute_search
                    • Calls search_web(query, limit=8)
                    • find-or-creates CrawlSource rows
                    • Emits search.executed
                    • Dispatches fetch_page per result
                    │
                    ▼
scraping_queue   ── app.tasks.crawl.fetch_page
                    • Calls fetch_url(url) (httpx or platform provider)
                    • Updates CrawlSource(status=scraped, html, ...)
                    • Emits page.fetched
                    • Dispatches extract_content
                    │
                    ▼
scraping_queue   ── app.tasks.crawl.extract_content
                    • Calls extract_role5_content(page)
                    • Updates CrawlSource(status=extracted, content, title)
                    • Emits content.extracted
                    • Dispatches extract_influencers
                    │
                    ▼
scoring_queue    ── app.tasks.extract.extract_influencers
                    • Calls extract_influencer_mentions(content)
                    • find-or-creates Influencer rows
                    • Emits influencer.found
                    • Dispatches score_influencer per new influencer
                    │
                    ▼
scoring_queue    ── app.tasks.score.score_influencer
                    • Calls run_role5_pipeline(candidate, campaign)
                    • Creates InfluencerScore row
                    • Emits score.calculated
                    • If severe brand-safety flag fired:
                      Dispatches classify_brand_safety
                    │
                    ▼
ai_agent_queue   ── app.tasks.score.classify_brand_safety
                    • Calls scan_brand_safety(text, source_url)
                    • Persists BrandSafetyFlag rows
                    • Emits brand_safety.flagged
```

The WebSocket handler at `app/api/websocket.py` subscribes to the
Redis pub/sub channel `campaign:{id}` and replays any events with
`event_id > last_event_id` on reconnect.

## Source tree

```text
.
├── app/                              # single FastAPI + Celery package
│   ├── main.py                       # FastAPI factory
│   ├── config.py                     # Pydantic settings
│   ├── celery_app.py                 # central Celery app + task_routes
│   ├── celery_factory.py             # per-service Celery app factory
│   ├── service_roles.py              # queue ↔ task mapping
│   ├── api/                          # FastAPI routers
│   ├── db/                           # models + alembic
│   ├── middleware/                   # CORS, structured logging
│   ├── schemas/                      # Pydantic request/response
│   ├── services/                     # redis_client, event_log, pipeline_state
│   └── tasks/                        # Celery task bodies (the pipeline)
│
├── ai_agent_services/worker.py       # celery_app = create_celery_app("ai_agent_service")
├── scraping_service/                 # domain code (search providers, fetcher, content extractor)
│   ├── crawling/
│   └── worker.py                     # celery_app = create_celery_app("scraping_service")
├── scoring_service/                  # role-5 deterministic scoring
│   ├── pipeline/                     # orchestrator
│   ├── identity/                     # name/URL resolution
│   ├── analysis/                     # fake-risk scorers
│   ├── detection/                    # detection classifier
│   ├── scoring/                      # fusion, trust formula, sub-scores
│   ├── extraction/                   # entities, contact info, credentials
│   ├── events/                       # ScoreCalculated event payload
│   └── worker.py                     # celery_app = create_celery_app("scoring_service")
│
├── umgl_ai/                          # OPTIONAL ML backend (install via `make umgl-install`)
│
├── tests/                            # pytest suite
├── scripts/                          # in-container integration scripts
├── Docs/                             # role / architecture docs
│
├── Dockerfile                        # single image
├── docker-compose.yml                # 7 services + infra
├── requirements.txt
├── alembic.ini
├── Makefile
├── ruff.toml
└── .env.example
```

## How the API ↔ Workers contract works

1. `app/celery_app.py` declares the central Celery app and
   `task_routes` from `app/service_roles.TASK_QUEUE_BY_NAME`. When
   the API calls `generate_queries.delay(campaign_id)`, the task
   lands in the right queue without needing an explicit
   `queue=` argument.
2. Each worker shim (`ai_agent_services/worker.py`, etc.) calls
   `create_celery_app(role)` **before** importing the task
   modules. `@shared_task` binds to the most recently created
   Celery instance, so this order is load-bearing.
3. `celery -A ai_agent_services.worker:celery_app worker
   -Q ai_agent_queue -c 2` consumes only from the role's queue.

## Optional ML backends (`umgl_ai`)

The `umgl_ai/` package at the repo root is **not** part of the
core dev image. The Docker build copies it into the image but does
not install it; the deps (`torch`, `transformers`, `peft`, ...)
are multi-GB and intentionally kept out.

To opt in:

```bash
# local install
make umgl-install

# or in the container
docker compose exec backend-core pip install -e /workspace/umgl_ai
```

Then enable the v2 adapter flags in `.env`:

```bash
UMGL_USE_SEMANTIC_V2=1
UMGL_USE_BEHAVIORAL_V2=1
UMGL_USE_LLM_EXPLAINER=1
```

The orchestrator detects the flags and routes the relevant signal
to the v2 engine; the heuristic path stays the deterministic
fallback. `MODEL_VERSION` in the score output flips to
`Role5-FakeDetectionScore-v2` when at least one v2 adapter fires.

## How to add a new Celery task

1. Pick a queue. The four queues are `ai_agent_queue`,
   `scraping_queue`, `scoring_queue`; the role boundaries are
   documented in `app/service_roles.py`. If your task does not
   fit any of them, add a new one there and a new worker
   container in `docker-compose.yml`.
2. Declare the task name and queue in
   `app/service_roles.TASK_QUEUE_BY_NAME` and
   `TASK_NAMES_BY_SERVICE`. The central `celery_app` reads these
   to build `task_routes` automatically.
3. Pick a module: `app/tasks/search.py` for query generation /
   search, `app/tasks/crawl.py` for I/O-heavy content fetching,
   `app/tasks/extract.py` for entity / identity work,
   `app/tasks/score.py` for the orchestrator and brand-safety
   work. Add a new file only if the task crosses domain
   boundaries (it should not).
4. Implement the task body with `@shared_task(name=..., bind=True,
   max_retries=N)`. Use the helpers from `app/tasks/_common.py`:
   - `db_session()` for the per-task DB session lifecycle
   - `publish_event(campaign_id, event_type, **payload)` for the
     WebSocket stream
   - `set_phase(campaign_id, **fields)` to bump the
     pipeline-state hash
   - `get_campaign(session, campaign_id)` to load the campaign
   - `campaign_query_payload(campaign)` to project the ORM row
     into the input shape the task body needs
5. Re-export the task from `app/tasks/__init__.py` so the API and
   `start_pipeline` can call it.
6. If a new worker consumes the queue, import the task module in
   the new worker shim **after** `create_celery_app(role)` is
   called (the order is load-bearing for `@shared_task`
   registration).
7. Add a test in `tests/test_celery_tasks.py` that exercises
   the task with `CELERY_TASK_ALWAYS_EAGER=True` and a mocked
   DB / Redis (see `_patched_db_session` in that file).
8. Update `Docs/Multiservice-Refactor.md` and
   `Docs/Role-5-Implementation.md` to mention the new task.

## How to add a new API endpoint

1. Add a route function in the appropriate `app/api/*.py` file.
   Use the existing `db: Session = Depends(get_db)` pattern for
   DB access and `from app.config import settings` for config.
2. If the endpoint emits events, call `publish_event` (sync
   helper from `app/services/event_log.py`) or `aemit_event`
   (async, for WebSocket handlers).
3. Add the OpenAPI expectations in `tests/test_app_smoke.py` so
   the smoke test continues to assert the route table.

## How to add a new scoring heuristic

1. The pure-Python scoring lives in `scoring_service/analysis/`.
   New heuristics go there as plain functions, no DB or Redis
   imports.
2. The orchestrator wires them together in
   `scoring_service/pipeline/orchestrator.py::run_role5_pipeline`.
   Add the new function call inside the same dict that
   `sub_scores` reads from, and surface the value in the
   `Role5PipelineResult` dataclass.
3. Add a unit test in `scoring_service/tests/` that exercises
   the heuristic in isolation.

## Observability

- `GET /health` — DB + Redis + Celery worker inspection
- `GET /api/campaigns/{id}/state` — pipeline-state hash
- `GET /ws/campaign/{id}` — live event stream with replay
- `make logs` — `docker compose logs -f backend-core`
- Flower on `http://localhost:5555` — Celery worker dashboard
- `app.tasks._common` uses `structlog` so all task bodies emit
  structured JSON (or key-value, depending on `APP_ENV`) to the
  container stdout.

## Security notes

- `app/middleware/cors.py` allows `localhost:3000`, `:3002`, and
  the API's own `:8000`/`:8002`. Production deployments must
  extend this list with the public frontend hostname.
- All Celery task bodies run in the same trust boundary as the
  worker process. Inputs from search results are treated as
  untrusted; the content extractor does not execute any HTML
  (only regex parsing).
- `app/services/event_log.py` and `pipeline_state.py` are
  best-effort: a Redis outage does not fail the pipeline. The
  `structlog` warning is the only signal.
