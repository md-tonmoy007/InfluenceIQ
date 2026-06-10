# Multi-Service Refactor

## What changed

The original repo shipped as a single Python backend image with four queue-specialized workers:

- `api`
- `worker_search`
- `worker_crawl`
- `worker_extract`
- `worker_score`

That worked for a modular monolith, but it did not match the team split described in the docs. The repo is now reorganized into application services aligned to ownership boundaries:

- `backend-core`
- `ai_agent_services`
- `scraping_service`
- `scoring_service`
- `frontend`

## Current boundaries

### backend-core

- FastAPI app
- shared Celery client for dispatch and worker inspection
- health endpoint exposing database, Redis, and worker queue state

### ai_agent_services

Owns:

- `app.tasks.search.generate_queries`
- `app.tasks.extract.resolve_identity_llm`
- `app.tasks.score.classify_brand_safety`

Queue:

- `ai_agent_queue`

### scraping_service

Owns:

- `app.tasks.search.execute_search`
- `app.tasks.crawl.fetch_page`
- `app.tasks.crawl.extract_content`

Queue:

- `scraping_queue`

### scoring_service

Owns:

- `app.tasks.extract.extract_influencers`
- `app.tasks.score.score_influencer`

Queue:

- `scoring_queue`

### frontend

- static Nginx-served shell
- reverse proxy from `/api/*` to `backend-core`

## Code organization

Shared code stays in `platform/app`:

- `config.py`
- `celery_factory.py`
- `service_roles.py`
- `tasks/*`
- `main.py`

Service-specific entrypoints live in:

- `backend_core/app.py`
- `ai_agent_services/worker.py`
- `scraping_service/worker.py`
- `scoring_service/worker.py`

## Why this is the right refactor for this repo

Most domain logic in the current codebase is still stubbed with `NotImplementedError`. Because of that, a full code extraction into independently versioned services would be artificial and would mostly duplicate placeholder code. This refactor keeps one shared source tree for now, while making the runtime topology explicitly multi-service and ready for later deep extraction as real implementations land.
