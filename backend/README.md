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

## Stripe Billing (Growth subscriptions)

Self-serve upgrades use **Stripe Checkout**; plan changes and cancellation use the **Customer Portal**. Webhooks sync state into the `subscriptions` table.

### Dashboard setup (one-time)

1. Create a **Growth** product with two recurring prices:
   - **Monthly:** $29.00 USD / month
   - **Annual:** $276.00 USD / year ($23/mo effective)
2. Enable the **Customer Portal** with cancellation, plan switching between the two Growth prices, and payment-method updates.
3. Register a webhook endpoint pointing at `/api/billing/webhook` with events:
   `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`

### Local webhook forwarding

```bash
stripe listen --forward-to localhost:8000/api/billing/webhook
```

Copy the `whsec_...` signing secret into `STRIPE_WEBHOOK_SECRET`.

### Environment variables (`backend/.env`)

```bash
STRIPE_SECRET_KEY=sk_test_...          # prefer rk_ restricted key in production
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_GROWTH_MONTHLY=price_...
STRIPE_PRICE_GROWTH_ANNUAL=price_...
FRONTEND_URL=http://localhost:3000
```

Billing endpoints return `503` when these are unset so the rest of the stack can run without Stripe configured.

### Search and platform providers (`backend/.env`)

Discovery (web search) and profile fetch use separate provider stacks. Full reference: [`docs/provider-configuration.md`](../docs/provider-configuration.md).

**Search** (`SEARCH_PROVIDER_MODE=auto`):

- Brave first, then SerpAPI as fallback

**Fetch** (per URL platform):

| Platform | Primary | Env keys |
| --- | --- | --- |
| YouTube | HTML + RSS | — |
| Instagram / TikTok / X | Apify (when token set) | `APIFY_API_TOKEN`, `APIFY_*_ACTOR` |
| Blogs / articles | scrape.do → httpx | `SCRAPE_DO_API` |

```bash
# Local dev (free search)
SEARCH_PROVIDER_MODE=auto
APP_ENV=dev

# Judges / production deploy
BRAVE_SEARCH_API_KEY=BSA...
APP_ENV=production
APIFY_API_TOKEN=apify_api_...
```
