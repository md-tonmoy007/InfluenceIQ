# InfluenceIQ

InfluenceIQ is an AI-powered trust-aware influencer discovery platform. The docs in [Docs/System-architecture.md](/home/rudy/Documents/codechamp_hackathon/InfluenceIQ/Docs/System-architecture.md:1) still describe the product and pipeline goals; this repo now packages that design as a multi-container, multi-service development stack.

## Service layout

- `backend-core`: FastAPI orchestration and health surface.
- `ai_agent_services`: Celery worker for LLM-oriented tasks.
- `scraping_service`: Celery worker for search, crawling, and content extraction.
- `scoring_service`: Celery worker for extraction and scoring tasks.
- `frontend`: lightweight Nginx-served UI that proxies `/api/*` to `backend-core`.

Shared Python code remains in [`platform/app`](/home/rudy/Documents/codechamp_hackathon/InfluenceIQ/platform/app:1), and the service-specific entrypoints live in [`backend_core`](/home/rudy/Documents/codechamp_hackathon/InfluenceIQ/backend_core:1), [`ai_agent_services`](/home/rudy/Documents/codechamp_hackathon/InfluenceIQ/ai_agent_services:1), [`scraping_service`](/home/rudy/Documents/codechamp_hackathon/InfluenceIQ/scraping_service:1), and [`scoring_service`](/home/rudy/Documents/codechamp_hackathon/InfluenceIQ/scoring_service:1).

## Run

```bash
docker compose up --build
```

Endpoints:

- Frontend: `http://localhost:3000`
- Backend core: `http://localhost:8000`
- Backend health: `http://localhost:8000/health`

## Notes

- The task implementations are still placeholders from the hackathon scaffold; this refactor changes runtime boundaries, queue ownership, and container topology.
- Queue routing is now service-oriented: `ai_agent_queue`, `scraping_queue`, and `scoring_queue`.
