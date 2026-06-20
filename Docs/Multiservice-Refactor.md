# Multi-Service Refactor

> **Status:** Complete (refactor landed in PR #9 and #10).
> The refactor was needed because the previous repo shipped as a single
> Python backend image whose file layout no longer matched the team
> boundaries in `Docs/Team-Overview.md`. The runtime topology is now
> explicitly multi-service, the source tree is one package, and the
> Celery pipeline is fully wired end-to-end.

## What changed (cumulative)

Three sequential refactor PRs produced the current layout:

1. **PR #9 — Consolidate** (`82af6e6`): merged `backend/`,
   `backend_core/`, and `platform/` into a single `backend/` package at
   the repo root. Deleted the orphan `backend/Dockerfile` and the
   `backend_core` import shim. Promoted `backend.ml` to a top-level
   package; deleted the 7 dead Rust service stubs.
2. **PR #10 — Wire Celery** (`fb854ef`): implemented the 8 Celery
   task bodies that `app/service_roles.py` declared but no code
   implemented. Replaced the `TODO` block in `app/api/campaigns.py`
   with `start_pipeline(campaign_id)`.
3. **PR #11 — Tests + Lint** (this PR): added `tests/test_app_smoke.py`
   and `tests/test_celery_tasks.py`, hardened `ruff.toml`, cleaned
   `.env.example`, added healthchecks + restart policies to
   `docker-compose.yml`, and wrote the docs that follow.

## Runtime topology

The deployment is a docker-compose cluster of seven containers
sharing two images:

```text
┌────────────────────────────────────────────────────────────────┐
│                   docker-compose cluster                       │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│   backend-core     ── uvicorn backend.api.main:app    (port 8000)     │
│   worker_ai_agent  ── celery -A ... -Q ai_agent_queue -c 2     │
│   worker_scraping  ── celery -A ... -Q scraping_queue -c 8     │
│   worker_scoring   ── celery -A ... -Q scoring_queue -c 4      │
│   flower           ── celery flower          (port 5555)        │
│   frontend         ── next.js dev            (port 3000)        │
│   postgres / redis / qdrant  (infra, no app code)              │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

All `backend-core` + worker containers share the same image (the
`Dockerfile` at the repo root) and the same `PYTHONPATH=/workspace`.

## Queue ↔ task mapping

The contract is encoded once in `app/service_roles.py` and the same
mapping drives both producers and consumers:

| Queue              | Worker                | Tasks                                                          |
| ------------------ | --------------------- | -------------------------------------------------------------- |
| `ai_agent_queue`   | `worker_ai_agent`     | `backend.pipeline.tasks.search.generate_queries`                            |
|                    |                       | `backend.pipeline.tasks.extract.resolve_identity_llm`                        |
|                    |                       | `backend.pipeline.tasks.score.classify_brand_safety`                        |
| `scraping_queue`   | `worker_scraping`     | `backend.pipeline.tasks.search.execute_search`                              |
|                    |                       | `backend.pipeline.tasks.crawl.fetch_page`                                   |
|                    |                       | `backend.pipeline.tasks.crawl.extract_content`                              |
| `scoring_queue`    | `worker_scoring`      | `backend.pipeline.tasks.extract.extract_influencers`                        |
|                    |                       | `backend.pipeline.tasks.score.score_influencer`                             |

Routing is enforced by `task_routes` on
:data:`backend.core.celery.app.celery_app` (the central app the API uses to
dispatch), and on each per-service app returned by
:func:`backend.core.celery.factory.create_celery_app`.

## Source tree

```text
.
├── app/                        # single FastAPI package
│   ├── main.py                 # FastAPI factory
│   ├── config.py               # Pydantic settings
│   ├── celery_app.py           # central Celery app + task_routes
│   ├── celery_factory.py       # per-service Celery app factory
│   ├── service_roles.py        # queue ↔ task mapping
│   ├── api/                    # FastAPI routers
│   │   ├── campaigns.py        # POST /api/campaigns dispatches start_pipeline
│   │   ├── health.py           # GET /health
│   │   ├── influencers.py
│   │   ├── demo.py
│   │   └── websocket.py        # /ws/campaign/{id}
│   ├── db/
│   │   ├── models.py
│   │   ├── session.py
│   │   └── migrations/         # alembic
│   ├── middleware/             # CORS, structured logging
│   ├── schemas/                # Pydantic request/response
│   ├── services/               # Redis + event log + pipeline state
│   │   ├── event_log.py        # sync + async emit_event / get_event_replay
│   │   ├── pipeline_state.py   # sync + async pipeline hash updates
│   │   └── redis_client.py
│   └── tasks/                  # Celery task bodies
│       ├── __init__.py         # re-exports + start_pipeline()
│       ├── _common.py          # shared helpers
│       ├── search.py           # generate_queries, execute_search
│       ├── crawl.py            # fetch_page, extract_content
│       ├── extract.py          # extract_influencers, resolve_identity_llm
│       └── score.py            # score_influencer, classify_brand_safety
│
├── backend.workers.ai_agent/worker.py # celery_app = create_celery_app("ai_agent_service")
├── backend.pipeline.content/worker.py  # celery_app = create_celery_app("backend.pipeline.content")
├── backend.pipeline/worker.py   # celery_app = create_celery_app("backend.pipeline")
│
├── backend.pipeline.content/crawling/  # domain code (search providers, fetcher, content extractor)
├── backend.pipeline/            # role-5 deterministic scoring (pipeline, identity, etc.)
│
├── backend.ml/                   # OPTIONAL ML backend (pip install -e ./backend.ml)
│
├── tests/
│   ├── test_role4_scraping.py
│   ├── test_role5.py
│   ├── test_celery_tasks.py    # EAGER chain integration test
│   └── test_app_smoke.py       # import-everything + route + Celery contract
│
├── scripts/
│   ├── test_suite.py           # in-container API integration suite
│   └── verify_websocket.py     # in-container WS replay test
│
├── Docs/                       # role / architecture docs
├── Dockerfile                  # single image for api + workers + flower
├── docker-compose.yml          # 7 services + infra
├── requirements.txt
├── alembic.ini
├── Makefile
├── ruff.toml
└── .env.example
```

## Service-specific entry points

| Service         | Module                                            | Command                                                                              |
| --------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------ |
| API             | `backend.api.main:app`                                    | `uvicorn backend.api.main:app --host 0.0.0.0 --port 8000`                                   |
| ai-agent worker | `backend.workers.ai_agent.worker:celery_app`             | `celery -A backend.workers.ai_agent.worker:celery_app worker -Q ai_agent_queue`             |
| scraping worker | `backend.pipeline.content.worker:celery_app`              | `celery -A backend.pipeline.content.worker:celery_app worker -Q scraping_queue`              |
| scoring worker  | `backend.pipeline.worker:celery_app`               | `celery -A backend.pipeline.worker:celery_app worker -Q scoring_queue`                |
| Flower          | `backend.workers.ai_agent.worker:celery_app`             | `celery -A backend.workers.ai_agent.worker:celery_app flower --port=5555`                   |
| backend.ml (opt.)  | `backend.ml.api:app`                                 | `make umgl` after `make umgl-install`                                                |

## Why this is the right refactor for this repo

* **One source tree, multiple services.** `backend/` is a single Python
  package shared by the API and all three workers. The packages at
  the repo root (`backend.workers.ai_agent/`, `backend.pipeline.content/`,
  `backend.pipeline/`) are 8-line shims that pick a service role
  and call `create_celery_app`. This matches the team boundaries
  in `Docs/Team-Overview.md` without the source duplication the
  earlier "extract every service" plan would have required.
* **The Celery pipeline is end-to-end functional.** Every task
  in `app/service_roles.py` now has a body in `app/tasks/`, and
  `POST /api/campaigns` actually triggers the chain.
* **The optional ML stack is opt-in.** `backend.ml` lives at the repo
  root; the core backend image has no torch / transformers /
  peft. The `UMGL_USE_*` env flags let ops roll the ML stack out
  per-tenant.
* **Lint and test are clean.** `ruff check .` is green and 144
  unit tests pass.
