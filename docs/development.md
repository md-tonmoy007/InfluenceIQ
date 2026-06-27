# Development Guide

This document is the practical local-development companion to [architecture.md](./architecture.md).

## Prerequisites

- Docker + Docker Compose
- Python 3.11+
- Node.js 20+
- `uv`
- `jq` optional, for prettier `make health` and `make seed` output

## Repository Layout

- `backend/` — FastAPI app, core infrastructure, pipeline logic, workers, tests
- `frontend/` — Next.js app
- `docs/` — architecture and team/reference docs
- `scripts/` — smoke and integration helpers

## Environment Setup

1. Copy `backend/.env.example` to `backend/.env`.
2. Review search and fetch provider keys — see [provider-configuration.md](./provider-configuration.md).
3. For frontend-only local work, review `frontend/.env.example`.
4. Create the backend environment with `uv sync --project backend --dev`.

The default Docker stack expects these exposed ports:

- Frontend: `3002`
- Backend API: `8002`
- Postgres: `5434`
- Redis: `6380`
- Qdrant: `6335`
- OpenSERP (optional search): `7000`
- Flower: `5555`

For local search without paid APIs, start OpenSERP:

```bash
docker compose up -d openserp
```

Set `OPENSERP_URL=http://openserp:7000` in `backend/.env` (see provider-configuration doc).

## Start The Full Stack

```bash
make up
```

Useful follow-up commands:

```bash
make ps
make logs
make health
make down
```

## Local Development Workflows

### Backend

Run fast offline tests without Docker:

```bash
make sync
make test-unit
```

Run linting:

```bash
make lint
```

Run container-backed API and websocket checks:

```bash
make test
make test-api
make test-pipeline
```

### Frontend

Install dependencies and run the Next.js dev server:

```bash
cd frontend
npm install
npm run dev
```

Default package scripts:

```bash
npm run lint
npm run build
npm run start
```

## Database And Migrations

Use the backend container for Alembic commands:

```bash
make db-revision
make db-upgrade
make migrate
```

## Demo Data

Seed or reset demo data through the API:

```bash
make seed
```

## Optional ML Package

The `backend/ml` package is optional.

```bash
make test-ml
make ml-run
```

Keep ML adapters disabled in `backend/.env` unless you have installed any extra ML dependencies you need and configured them.

## Development Conventions

- Treat `docs/architecture.md` as the system source of truth.
- Keep the runtime queue model aligned with the current three-queue design:
  - `ai_agent_queue`
  - `scraping_queue`
  - `scoring_queue`
- Prefer deterministic behavior when optional ML or LLM adapters are unavailable.
- Keep API contracts, Redis event shapes, and persistence models synchronized across backend and frontend work.

## Troubleshooting

- If `make health` fails, confirm `make ps` shows healthy `postgres`, `redis`, and `backend-core` containers.
- If frontend requests fail in Docker, verify `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_WS_BASE_URL` are set correctly.
- If offline Python tests fail immediately, check that the local Python environment can import `backend` and that required test dependencies are installed.
- If Celery-related flows stall, inspect `flower` on port `5555` and the worker container logs.
