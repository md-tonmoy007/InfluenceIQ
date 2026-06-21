# Team Ownership Overview

**Project:** InfluenceIQ  
**Team Size:** 4 people  
**Canonical Architecture:** [Architecture.md](Architecture.md)

This document describes current-state ownership for the implemented system. It is not a build schedule. Each role owns a durable part of the product, its contracts, and the operational seams other roles depend on.

## Roles

| Role | Focus | Owns | Primary interfaces |
| --- | --- | --- | --- |
| Platform + Orchestration | Runtime topology, queues, config, deployment, observability | Docker, env/config, Redis, Celery app and routes, worker topology, health and logging | Celery task routing, Redis `pipeline_state:{campaign_id}`, Redis `pipeline_events:{campaign_id}` |
| Frontend | Brand-facing product surface | Next.js routes, campaign submission UX, live pipeline progress UX, recommendation and profile views, API/WebSocket client behavior | REST payloads, WebSocket event envelope, reconnect with `last_event_id` |
| Backend API + Data | Public API surface and durable data model | FastAPI routers, request/response schemas, DB models and migrations, event replay surface, campaign state read APIs | REST contracts, WebSocket endpoint, PostgreSQL persistence contracts |
| Pipeline Intelligence | Search-to-score domain logic | Search normalization, fetch/extract flow, provenance, influencer extraction, identity resolution, scoring, safety classification, ranking inputs | Task payloads, candidate/enrichment payloads, score/provenance persistence expectations |

## Coordination Contracts

These are the shared contracts that must stay stable across roles.

| Contract | Source of truth | Producers | Consumers |
| --- | --- | --- | --- |
| REST request and response payloads | `backend/api/schemas/`, `backend/api/routers/` | Backend API + Data | Frontend, Platform for health/testing |
| WebSocket event envelope | `docs/Architecture.md`, `backend/api/schemas/ws_event.py`, `backend/core/cache/event_log.py` | Backend API + Data, Pipeline Intelligence | Frontend |
| Redis pipeline state | `backend/core/cache/pipeline_state.py` | Platform + Orchestration, Pipeline Intelligence task adapters | Backend API + Data, Frontend via REST/WebSocket |
| Redis event replay log | `backend/core/cache/event_log.py` | Pipeline task adapters | Backend API + Data, Frontend |
| Queue routing and worker topology | `backend/core/celery/roles.py`, `backend/workers/` | Platform + Orchestration | Backend API + Data, Pipeline Intelligence |
| Score and provenance persistence | `backend/core/database/models.py` | Pipeline Intelligence, Backend API + Data | Frontend, Backend API + Data |

## Shared Rules

- The architecture source of truth is [Architecture.md](Architecture.md). Role docs summarize ownership; they do not redefine the system.
- The operational queue model is fixed at three queues unless the architecture changes:
  - `ai_agent_queue`
  - `scraping_queue`
  - `scoring_queue`
- WebSocket clients reconnect with `last_event_id` and must receive the same event envelope shape on replay and live delivery.
- Redis `pipeline_state` is fast status, not a replacement for durable PostgreSQL records.
- Source provenance and score outputs must stay linked. Recommendations are only valid if the stored score can still be traced back to sources and campaign context.
- Optional ML and LLM adapters may enrich the pipeline, but deterministic paths remain the baseline contract.

## Role Boundaries

- Platform + Orchestration owns runtime reliability and queue correctness, not campaign-specific scoring logic.
- Frontend owns presentation and interaction flows, not business-rule duplication or alternative scoring formulas.
- Backend API + Data owns public API contracts and durable persistence, not search heuristics or scoring-policy internals.
- Pipeline Intelligence owns extraction, identity, scoring, and safety logic, not deployment topology or frontend rendering.

## Active Role Docs

- [Role 1: Platform + Orchestration](Role-1-AI-DevOps.md)
- [Role 2: Frontend](Role-2-Frontend.md)
- [Role 3: Backend API + Data](Role-3-Backend.md)
- [Role 4: Pipeline Intelligence](Role-4-Pipeline-Intelligence.md)
