# InfluenceIQ

**InfluenceIQ** is a trust-aware AI platform for influencer discovery. It helps brands and agencies move beyond follower counts by discovering creators, gathering public evidence, scoring trust and relevance, and producing a ranked shortlist with explainable signals.

> SciBlitz AI Challenge 2026 submission  
> **Team:** sudo_make_it_work  
> **Institution:** Rajshahi University of Engineering & Technology (RUET)  
> **Track:** D — Open Innovation

## Live Submission Links

- **Live demo:** https://cuet.shafayetsadi.dev/
- **Project report:** [`docs/project-report.md`](docs/project-report.md)
- **Model & data card:** [`docs/model-data-card.md`](docs/model-data-card.md)
- **Architecture:** [`docs/architecture.md`](docs/architecture.md)
- **Pipeline flow:** [`docs/pipeline-flow-architecture.md`](docs/pipeline-flow-architecture.md)
- **Deployment guide:** [`docs/deploy-digitalocean.md`](docs/deploy-digitalocean.md)

## Problem

Influencer selection is often driven by surface metrics such as follower count, likes, and visibility. That creates real risks:

- inflated influence from fake followers or low-quality engagement,
- hidden brand-safety concerns,
- slow manual research across platforms,
- weak justification for why a creator was selected.

InfluenceIQ addresses this by turning creator discovery into an **evidence-backed, trust-aware AI workflow**.

## What InfluenceIQ Does

A user can:

- create a campaign brief,
- launch an asynchronous discovery pipeline,
- monitor live progress through REST state and WebSocket events,
- review ranked influencer recommendations,
- inspect creator profiles and supporting evidence,
- save creators to lists and track outreach/contract state,
- run deep analysis on shortlisted creators.

## Core AI Idea

InfluenceIQ does **not** rank creators by popularity alone. It combines multiple signals into a trust-aware score:

- relevance,
- credibility,
- engagement quality,
- sentiment,
- brand safety,
- source confidence,
- fake-risk penalties and evidence caps.

The system is **deterministic-first** with optional model-backed components. If LLM or ML providers are unavailable, the platform falls back to heuristics instead of failing the pipeline.

## Current Architecture

InfluenceIQ is implemented as a **modular monolith** with multiple runtime roles:

- **Frontend:** Next.js App Router (`frontend/`)
- **Backend API:** FastAPI (`backend/api/`)
- **Database:** PostgreSQL
- **Broker / state / replay:** Redis
- **Async workers:** Celery
- **Optional services:** Qdrant and `backend/ml`

### Worker queues

- `ai_agent_queue` — query planning, LLM-assisted tasks, deep analysis
- `scraping_queue` — search, crawling, content fetch/extraction, enrichment
- `scoring_queue` — extraction, clustering, scoring, persistence

For the full current-state system map, see [`docs/architecture.md`](docs/architecture.md).

## Pipeline Overview

Main campaign flow:

```text
Campaign brief
  -> query generation
  -> web discovery
  -> page fetch
  -> content extraction
  -> influencer extraction
  -> identity resolution
  -> platform enrichment
  -> trust-aware scoring
  -> ranked shortlist + live progress events
```

Deep-analysis flow:

```text
Shortlisted influencer
  -> collect social content
  -> collect comments
  -> collect external signals
  -> synthesize report
  -> re-score with richer evidence
```

Detailed behavior is documented in [`docs/pipeline-flow-architecture.md`](docs/pipeline-flow-architecture.md).

## Repository Structure

```text
frontend/                  Next.js application
backend/api/               FastAPI routes and schemas
backend/core/              config, auth, DB, Redis, Celery, billing
backend/pipeline/          discovery, extraction, enrichment, scoring, deep analysis
backend/workers/           Celery worker entrypoints
backend/ml/                optional ML adapters/services
backend/tests/             tests
docs/                      architecture, report, deployment, reference docs
scripts/                   helpers and smoke scripts
```

## Local Development

### Prerequisites

- Docker + Docker Compose
- Python 3.11+
- Node.js 20+
- `uv`

### Setup

```bash
cp backend/.env.example backend/.env
uv sync --project backend --dev
```

### Run the full stack

```bash
make up
```

### Default local endpoints

- Frontend: `http://localhost:3002`
- Backend API: `http://localhost:8002`
- Health: `http://localhost:8002/health`
- Flower: `http://localhost:5555`

### Common commands

```bash
make ps
make logs
make health
make down
make test-unit
make test
make test-pipeline
make lint
```

More details: [`docs/development.md`](docs/development.md)

## Deployment

This repository includes a production deployment path for a **single DigitalOcean Droplet** using Docker Compose.

Production guide:

- [`docs/deploy-digitalocean.md`](docs/deploy-digitalocean.md)

The deployment model runs:

- frontend,
- backend API,
- Celery workers,
- PostgreSQL,
- Redis,
- optional Qdrant,
- Caddy for HTTPS.

## AI / Model / Data Notes

InfluenceIQ primarily works on **publicly available inference-time data** collected during campaign execution. It does not rely on a proprietary training dataset.

Supported/used provider and model paths include:

- Brave Search / SerpAPI,
- Apify-backed platform enrichment,
- scrape.do / direct HTTP fetch,
- optional Hugging Face and OpenRouter-backed model adapters,
- optional embeddings and semantic relevance support.

See the submission data card:

- [`docs/model-data-card.md`](docs/model-data-card.md)

## Submission-Oriented Highlights

This project was built to satisfy the SciBlitz AI Challenge expectations for:

- **meaningful AI integration** in the core workflow,
- **public live deployment**,
- **clear architecture and technical implementation**,
- **real-world impact** through trust-aware creator selection,
- **documentation and explainability** through report, data card, and repository docs.

## Team

- **MD Tonmoy Hossain Jifat** — Pipeline intelligence, scoring logic, trust/risk design
- **Shafayetul Huda Sadi** — Backend platform, orchestration, frontend integration, deployment
- **Adib Hasan** — Frontend implementation
- **Mahmudul Hasan** — Scraping and scoring implementation

## License / Attribution

This repository uses third-party libraries, APIs, and pretrained models where applicable. Relevant references, model details, and data-source notes are documented in:

- [`docs/model-data-card.md`](docs/model-data-card.md)
- [`docs/provider-configuration.md`](docs/provider-configuration.md)

---

For judges and reviewers, the best starting points are:

1. the **live demo**,
2. [`docs/project-report.md`](docs/project-report.md),
3. [`docs/architecture.md`](docs/architecture.md),
4. [`docs/model-data-card.md`](docs/model-data-card.md).
