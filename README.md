# InfluenceIQ

InfluenceIQ is an AI-powered trust-aware influencer discovery platform. The docs in [Docs/Architecture.md](Docs/Architecture.md) describe the product and pipeline goals; this repo packages that design as a multi-container, multi-service development stack.

## Service layout

- `backend-core`: FastAPI orchestration and health surface (entrypoint: `backend.api.main:app`).
- `worker_ai_agent`: Celery worker for LLM-oriented tasks (entrypoint: `backend.workers.ai_agent.worker:celery_app`).
- `worker_scraping`: Celery worker for search, crawling, and content extraction (entrypoint: `backend.workers.scraping.worker:celery_app`).
- `worker_scoring`: Celery worker for extraction and scoring tasks (entrypoint: `backend.workers.scoring.worker:celery_app`).
- `frontend`: lightweight Next.js UI that proxies `/api/*` to `backend-core`.

All Python backend code is grouped under `backend/` with four layers:

- `backend.api/` — FastAPI surface (routers, schemas, middleware)
- `backend.core/` — cross-cutting infrastructure (config, db, cache, celery setup)
- `backend.pipeline/` — role-5 domain (orchestrator, tasks, analysis, detection, fusion, content)
- `backend.workers/` — per-role Celery shims
- `backend.ml/` — *optional* ML backend kept in-tree

## Python environment

```bash
cp backend/.env.example backend/.env
uv sync --project backend --dev
```

This repo now uses `backend/pyproject.toml` and `backend/uv.lock` as the Python source of truth.

## Run

```bash
make up
```

Endpoints:

- Frontend: `http://localhost:3002`
- Backend core: `http://localhost:8002` (mapped to `8000` inside the container)
- Backend health: `http://localhost:8002/health`

## Tests

```bash
make sync        # create/update the backend uv environment
make test-unit   # fast offline tests (no docker required)
make test-ml     # optional backend.ml tests
```

## Notes

- The task implementations are still placeholders from the hackathon scaffold; this refactor changes runtime boundaries, queue ownership, and container topology.
- Queue routing is service-oriented: `ai_agent_queue`, `scraping_queue`, and `scoring_queue`.
- `backend/ml` is optional at runtime. Its heavier ML dependencies are intentionally not part of the default backend sync, and adapters fall back to deterministic behaviour when unavailable.
