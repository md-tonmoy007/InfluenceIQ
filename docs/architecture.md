# InfluenceIQ Architecture

This document describes the architecture that exists in the current repository. It is a current-state reference for the checked-in codebase, not a target-state wishlist.

## System Overview

InfluenceIQ is a full-stack influencer discovery application built as a modular monolith:

- a `Next.js` App Router frontend in `frontend/`
- a `FastAPI` backend in `backend/api/`
- a `PostgreSQL` database for durable product data
- `Redis` for Celery brokering, transient pipeline state, replayable event logs, and idempotency/cache helpers
- three Celery worker roles for async campaign processing
- optional `Qdrant` and `backend/ml` services for heavier semantic or model-backed workflows

The main product flow is:

1. A user signs up or logs in.
2. They create a campaign brief or run a natural-language discover search.
3. The backend creates a campaign row and dispatches async pipeline work.
4. Workers discover sources, extract creator signals, resolve identities, score candidates, and persist results.
5. The frontend polls REST endpoints and subscribes to a campaign WebSocket stream for live progress.
6. Users review matches, save creators to lists, mark contracts, and optionally trigger deeper report generation for a shortlisted influencer.

## Repository Layout

```text
frontend/                  Next.js application
backend/api/               FastAPI routes, schemas, middleware
backend/core/              config, auth, database, Redis, Celery, billing, lifecycle
backend/pipeline/          discovery, extraction, enrichment, scoring, deep analysis
backend/workers/           Celery worker entrypoints per queue
backend/ml/                optional model-serving and ML adapters
backend/tests/             API, pipeline, ML, and integration tests
docs/                      architecture and role-specific documentation
scripts/                   smoke and seed helpers
```

## Runtime Topology

```text
Browser
  |
  v
Next.js frontend
  |
  +-- REST -> FastAPI backend
  +-- WebSocket -> /ws/campaign/{campaign_id}
           |
           v
       FastAPI app
           |
           +-- PostgreSQL
           +-- Redis
           +-- Celery dispatch
                  +-- ai_agent_queue
                  +-- scraping_queue
                  +-- scoring_queue
           +-- optional Stripe integration
           +-- optional Qdrant + ML service
```

In local Docker Compose, the stack runs as:

- `frontend` on port `3002`
- `backend-core` on port `8002`
- `postgres` on `5434`
- `redis` on `6380`
- `flower` on `5555`
- optional `ml-service` on `8082`
- optional `qdrant` on `6335` and `6336`

## Frontend Architecture

The frontend is a single Next.js application using the App Router. It has two broad surface areas.

### Public and Auth Surfaces

- `/` is the marketing landing page.
- `/signup` and `/login` handle account creation and session entry.
- `/onboarding` captures the brand profile through `OnboardingStepper`.

Auth state is managed in the browser and backed by backend-issued JWT cookies and token responses. The frontend API client lives in `frontend/src/lib/api.ts`, and the WebSocket URL builder lives in `frontend/src/lib/websocket.ts`.

### Authenticated Workspace

Most signed-in pages render inside `frontend/src/components/shell/AppShell.tsx`, which provides:

- `AuthGate` protection
- shared sidebar and topbar chrome
- workspace summary counts loaded from `/api/workspace/summary`

Current workspace routes include:

- `/dashboard` for workspace summary and recent activity
- `/briefs` and `/briefs/new` for campaign creation and campaign history
- `/discover` for search-first creator discovery
- `/shortlist` for campaign-specific shortlisted creators
- `/lists` for saved creator lists
- `/settings` for profile, brand, notifications, integrations, API keys, and billing
- `/profile/[id]` for an influencer profile in campaign context
- `/report/[influencerId]` for deep-analysis reports
- `/matching` and `/pipeline-debug` as workflow/debug surfaces

The frontend is not just a thin renderer. It owns route composition, page-specific interaction logic, optimistic UI, and presentation adapters, but it treats backend responses as the source of truth for business state.

## Backend Architecture

The backend boots in `backend/api/main.py` and registers:

- middleware for CORS, request logging, and error envelopes
- routers for auth, billing, health, onboarding, settings, campaigns, influencers, lists, workspace, demo, and websocket
- startup validation through `backend.core.lifecycle`

### API Layer

The API layer is organized by resource:

- `auth`: signup, login, logout, current-user profile, password change, refresh
- `onboarding`: brand-profile create/read
- `settings`: notifications, integrations, API keys, subscription reads/updates
- `billing`: Stripe Checkout, Customer Portal, webhook ingestion
- `campaigns`: create, list, retrieve, update, submit, rerun, cancel, duplicate, delete, facets, influencers, contracts, state
- `influencers`: profile, score history, safety flags, credential verifications, deep analysis
- `lists`: saved-list CRUD and list item management
- `workspace`: dashboard summary and activity feed
- `health`: liveness/readiness and queue visibility
- `websocket`: replayable campaign event stream
- `demo`: development/demo seed endpoints

### Core Infrastructure

`backend/core/` contains the shared infrastructure:

- `config.py` for environment-driven settings
- `auth.py` for JWT issuance and user auth helpers
- `database/` for SQLAlchemy models, sessions, and Alembic migrations
- `cache/` for Redis-backed pipeline state, event log, idempotency, and campaign cache helpers
- `celery/` for queue definitions, routing, and app creation
- `billing/` for Stripe integration and subscription sync

This is a modular monolith. There is one backend codebase and one primary data model, with boundaries expressed as Python modules rather than separate deployable services.

## Data Model

The durable model in `backend/core/database/models.py` has six major areas.

### 1. Account and Brand Data

- `User`
- `BrandProfile`
- `NotificationPreference`
- `IntegrationConnection`
- `ApiKey`
- `Subscription`

The current product is fundamentally user-scoped. Some tables already have placeholders like `org_id`, but workspace and settings flows are implemented around the current authenticated user rather than a full multi-tenant org model.

### 2. Campaign Lifecycle

- `Campaign`
- `CampaignContract`

Campaigns store the brief snapshot, search query, entry point, preferred platforms, budget range, scoring weights, and lifecycle timestamps. Contracts attach outreach state to `(campaign, influencer)` pairs.

### 3. Influencer Catalog and Provenance

- `Influencer`
- `PlatformProfile`
- `PlatformPost`
- `PlatformComment`
- `CrawlSource`
- `CrawlSourceInfluencer`
- `IdentityMerge`

This split is important:

- canonical influencer identity lives on `Influencer`
- discovered URLs and extracted content live on `CrawlSource`
- many-to-many attribution between sources and influencers lives on `CrawlSourceInfluencer`
- richer structured platform snapshots live on `PlatformProfile`, `PlatformPost`, and `PlatformComment`

### 4. Scoring and Trust Signals

- `InfluencerScore`
- `BrandSafetyFlag`
- `CredentialVerification`
- `CandidateSnapshot`

Scores are versioned and carry sub-scores, reasons, provenance, and model metadata. Brand-safety and credential evidence are durable records, not frontend-only annotations.

### 5. Deep Analysis

- `DeepAnalysisRun`
- `DeepAnalysisPostResult`
- `DeepAnalysisReport`

Deep analysis is a separate on-demand workflow layered on top of the main campaign scoring flow. It reuses previously collected platform/profile/post/comment data where possible and caches completed reports for a bounded freshness window.

### 6. Workspace Curation

- `SavedList`
- `SavedListItem`

Lists are user-owned collections of creators, optionally tied back to the campaign they were saved from through `source_campaign_id`.

## Async Campaign Pipeline

The main async entrypoint is `backend.pipeline.tasks.orchestrator.start_campaign()`. `POST /api/campaigns` either:

- creates a draft campaign and stops, or
- creates a running campaign, initializes Redis pipeline state, and dispatches the worker pipeline

### Queue Roles

Celery task routing is defined in `backend/core/celery/roles.py`:

- `ai_agent_queue`
  - query generation
  - LLM-assisted identity resolution
  - LLM-assisted brand-safety classification
  - deep analysis
- `scraping_queue`
  - search execution
  - page fetch and extraction
  - influencer platform enrichment
- `scoring_queue`
  - influencer extraction
  - identity clustering
  - candidate scoring

### Pipeline Stages

The pipeline code under `backend/pipeline/tasks/` and `backend/pipeline/` currently breaks down into these functional phases:

1. query generation
2. search execution and URL discovery
3. page fetch and content extraction
4. influencer extraction from content
5. identity resolution and canonicalization
6. platform enrichment
7. score computation and safety analysis
8. persistence of campaign results and progress events

The supporting domain code is grouped by concern:

- `content/` for discovery, fetch, parsing, provider access, and enrichment
- `extraction/` for social handles, entities, and contact information
- `identity/` for canonical identity resolution
- `analysis/` for trust, sentiment, fake engagement, and related heuristics
- `detection/` for specific detector modules
- `fusion/` for scoring and weighted aggregation
- `candidate/` for building richer per-influencer candidate objects

## Campaign State and Realtime Events

Campaign progress is represented in two Redis-backed forms:

- a pipeline-state hash for cheap polling
- an ordered event log for WebSocket replay

The live stream is `ws://.../ws/campaign/{campaign_id}?last_event_id=N`.

Current behavior:

- the server replays missed events when `last_event_id` is supplied
- it then subscribes the client to the live Redis pub/sub channel
- it emits heartbeat frames every 20 seconds
- it enforces a bounded send queue and disconnects slow consumers

This is the canonical realtime path for campaign execution progress. The frontend can recover from disconnects by reconnecting with the last seen event id.

## Deep Analysis Workflow

Deep analysis is a second asynchronous workflow exposed from `backend/api/routers/influencers.py`:

- `POST /api/influencers/{id}/deep-analysis`
- `GET /api/influencers/{id}/deep-analysis/latest`
- `GET /api/influencers/{id}/deep-analysis/{run_id}`
- `GET /api/influencers/{id}/reports/{report_id}`

The Celery task in `backend/pipeline/tasks/deep.py` runs four stages inside one job:

1. collect social content
2. collect post comments
3. collect external signals
4. synthesize the final report

It emits progress events such as:

- `deep_analysis.started`
- `deep_analysis.social_collected`
- `deep_analysis.comments_collected`
- `deep_analysis.external_signals_collected`
- `deep_analysis.report_ready`
- `deep_analysis.failed`

After a successful report, the backend re-enqueues a creator rescore so the richer evidence can influence trust output in the main campaign view.

## External Integrations

### Search and Scraping

The repository currently supports a mix of providers:

- Brave Search and SerpAPI for web discovery
- Apify-backed profile/comment collection for Instagram, TikTok, and X
- scrape.do or plain HTTP fetch for article pages
- YouTube-specific collection using its own provider path

The provider surface is environment-driven and documented further in [provider-configuration.md](./provider-configuration.md).

### Billing

Stripe is wired for:

- Checkout session creation
- Customer Portal access
- webhook-driven subscription synchronization

Billing is optional in development; endpoints return degraded behavior when Stripe secrets are not configured.

### Optional ML and Vector Services

`backend/ml/` and Qdrant are optional enhancements rather than required runtime dependencies for the core product flow. The main backend and worker pipeline still have deterministic fallbacks for many tasks.

## Deployment Model

The checked-in deployment model is container-oriented:

- one image for the API and worker processes
- one Next.js frontend container
- one PostgreSQL container
- one Redis container
- optional Flower, Qdrant, and ML containers

The API and worker services share the same backend code and differ mainly by startup command and queue subscription.

## Current Architectural Boundaries

These boundaries are true in the current codebase and should guide future updates to this document:

- The product is one codebase with multiple process roles, not a microservice system.
- The primary source of truth is PostgreSQL; Redis holds transient state, replay logs, and fast coordination data.
- User ownership is enforced in most workspace flows; full org/team tenancy is not yet the main execution model.
- Deep analysis is an extension of the existing campaign pipeline, not a separate subsystem with its own transport.
- Saved lists, campaign contracts, settings, and billing are part of the same product backend, not external admin tooling.

## Related Docs

- [pipeline-flow-architecture.md](./pipeline-flow-architecture.md)
- [provider-configuration.md](./provider-configuration.md)
- [development.md](./development.md)
- [Role-3-Backend.md](./Role-3-Backend.md)
- [Role-2-Frontend.md](./Role-2-Frontend.md)
- [Role-4-Pipeline-Intelligence.md](./Role-4-Pipeline-Intelligence.md)
