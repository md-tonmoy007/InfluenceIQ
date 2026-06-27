# InfluenceIQ Backend

Python backend for the trust-aware influencer discovery platform. Canonical architecture reference: [`docs/architecture.md`](../docs/architecture.md).

## Layout

```text
api/          HTTP + WebSocket entrypoints (FastAPI)
core/         Config, database, Redis, Celery factory, cache
pipeline/     Discovery, scoring, detection, fusion (domain logic)
workers/      Thin Celery process bootstrappers (one per queue)
demo/         Dev smoke tests and database seed helpers
ml/           Optional model-serving backends (see ml/README.md)
tests/        Unit and integration tests
```

## Where does X live?

| Question | Location |
| -------- | -------- |
| REST routes and schemas | `api/routers/`, `api/schemas/` |
| Campaign / influencer models | `core/database/models.py` |
| Celery queue routing | `core/celery/roles.py` |
| Pipeline task bodies | `pipeline/tasks/` |
| Scoring orchestrator (sync, no I/O) | `pipeline/orchestrator/pipeline.py` → `run_role4_pipeline` |
| Optional ML adapters | `pipeline/fusion/backends/ml_adapters.py` |
| Worker entrypoints | `workers/{ai_agent,scraping,scoring}/worker.py` |
| Demo seed / smoke logic | `demo/` (router in `api/routers/demo.py`) |

## Runtime topology

```text
Browser → frontend → backend-core (FastAPI)
                         ├── PostgreSQL
                         ├── Redis (broker + pipeline state + events)
                         ├── worker_ai_agent   → ai_agent_queue
                         ├── worker_scraping     → scraping_queue
                         ├── worker_scoring      → scoring_queue
                         └── ml-service (optional) → backend.ml.api
```

Workers and the API share one codebase and Docker image; only the process `command` differs. The ML service uses `backend/Dockerfile.ml` with the `[ml]` optional dependency group.

## Local development

```bash
# Core stack (from repo root)
docker compose up -d

# Optional ML inference service (heavy image — torch/transformers)
docker compose --profile ml up -d ml-service

# Run backend tests
cd backend && pytest tests/ -q
```

API: `http://localhost:8002` · ML service: `http://localhost:8082` · Flower: `http://localhost:5555`

## Pipeline entry point

Role-4 pipeline intelligence runs synchronously via:

```python
from backend.pipeline.orchestrator import run_role4_pipeline

result = run_role4_pipeline(candidate_dict, campaign_dict)
```

Celery tasks in `pipeline/tasks/` wrap this for async campaign execution. See [`docs/Role-4-Pipeline-Intelligence.md`](../docs/Role-4-Pipeline-Intelligence.md).

## Optional ML

`backend/ml` is optional. The scoring pipeline uses deterministic heuristics by default and only calls ML when env flags are set (`ML_USE_SEMANTIC_V2`, etc.). See [`ml/README.md`](ml/README.md).
