# Role 3: Backend API + Database Engineer

**Architecture Sections Owned:** 4 (backend stack), 5 (API layer), 18 (WebSocket server), 19 (database)

You are the glue between every component. Frontend reads from you, Celery workers write through you, Redis state is queried via you.

---

## Responsibilities

- PostgreSQL schema: all tables (campaigns, influencers, influencer_scores, crawl_sources, brand_safety_flags)
- SQLAlchemy models + Alembic migrations
- FastAPI REST endpoints (campaign CRUD, influencer retrieval, dashboard data)
- WebSocket server + event broadcast to subscribed clients
- WebSocket reconnection: event replay from Redis list
- Pipeline state polling endpoint (REST fallback if WebSocket fails)
- Authentication stub (single-user or API key — keep minimal for hackathon)

---

## 7-Day Todo List

### Day 1 — Schema + Skeleton

- [ ] Define PostgreSQL schema (matches `System-architecture.md` Section 19)
  - `campaigns`, `influencers`, `influencer_scores`, `crawl_sources`, `brand_safety_flags`
- [ ] Write SQLAlchemy models with relationships
- [ ] Set up Alembic, generate initial migration, apply to dev DB
- [ ] Scaffold FastAPI app with empty route handlers for all endpoints
- [ ] Publish WebSocket event JSON schema to frontend + AI/DevOps lead
- [ ] Add CORS middleware (allow Next.js dev origin)

### Day 2 — Core REST Endpoints

- [ ] `POST /api/campaigns` — create campaign, dispatch root Celery task, return campaign_id
- [ ] `GET /api/campaigns/{id}` — return campaign + current pipeline state from Redis
- [ ] `GET /api/campaigns/{id}/influencers` — return scored influencers (paginated)
- [ ] `GET /api/campaigns/{id}/state` — return pipeline state hash (REST fallback)
- [ ] Add Pydantic request/response models matching frontend contract
- [ ] Test with curl: full campaign create → state poll loop works

### Day 3 — WebSocket Server

- [ ] WebSocket endpoint at `/ws/campaign/{campaign_id}`
- [ ] On connect: subscribe to Redis pub/sub channel `campaign:{id}`
- [ ] On Celery worker publishes event → forward to all subscribed clients
- [ ] Append every event to Redis list `pipeline_events:{campaign_id}` (TTL 1h)
- [ ] Handle client disconnect cleanly (unsubscribe, no resource leaks)

### Day 4 — Reconnection Replay

- [ ] On WebSocket connect, accept `?last_event_id=N` query param
- [ ] If param present: replay all events from Redis list with ID > N
- [ ] Then attach to live pub/sub feed for new events
- [ ] Test scenario: kill WebSocket mid-pipeline, reconnect, verify all events received
- [ ] Add heartbeat/ping every 20s to detect dead connections

### Day 5 — Integration + Data Flow

- [ ] Verify Celery workers can write to PostgreSQL via shared SQLAlchemy session
- [ ] Verify Celery workers can publish events to Redis that reach WebSocket clients
- [ ] Add filtering query params to `GET /influencers`: platform, niche, region, grade, follower_size
- [ ] Implement source provenance JOIN: each influencer response includes `sources[]`
- [ ] Add request logging middleware (timing, status codes)

### Day 6 — Hardening

- [ ] Add database indexes (campaign_id on influencer_scores, source_url on crawl_sources)
- [ ] Add pagination + sort to influencer endpoint (default: by final_score DESC)
- [ ] Handle edge cases: campaign not found (404), pipeline still running (200 with partial), pipeline failed (200 with partial + error flag)
- [ ] Add `GET /health` integration with AI/DevOps lead's monitoring endpoint
- [ ] Test 3 full campaigns end-to-end via API

### Day 7 — Demo Prep

- [ ] Seed database with 2–3 pre-cached demo campaign results
- [ ] Add `/api/demo/reset` endpoint to restore clean demo state quickly
- [ ] Verify all queries respond in under 200ms on demo data
- [ ] Help frontend debug any last-minute integration issues
- [ ] Document API in a short README for judges

---

## Key Files You Own

```
platform/
├── main.py                   (FastAPI entrypoint)
├── api/
│   ├── campaigns.py
│   ├── influencers.py
│   ├── websocket.py
│   └── health.py
├── db/
│   ├── models.py             (SQLAlchemy)
│   ├── session.py
│   └── migrations/           (Alembic)
├── schemas/                  (Pydantic)
│   ├── campaign.py
│   ├── influencer.py
│   └── events.py
├── services/
│   ├── pipeline_state.py     (Redis state read/write)
│   └── event_log.py          (Redis event list read/write)
└── middleware/
    ├── cors.py
    └── logging.py
```

---

## Daily Dependencies

| Day | What You Need From Whom |
|-----|-------------------------|
| 1 | Redis key schema (AI/DevOps), Influencer data model JSON (Scoring) |
| 2 | Celery task signatures to dispatch (AI/DevOps) |
| 3 | Celery workers publishing events to Redis channels (AI/DevOps) |
| 5 | Workers writing to DB tables (Scraping, Scoring) |

---

## WebSocket Event Schema (You Define This)

```json
{
  "event_id": 42,
  "type": "score.calculated",
  "campaign_id": "abc-123",
  "timestamp": "2026-05-21T10:30:00Z",
  "payload": {
    "influencer_id": "uuid",
    "final_score": 87.5,
    "grade": "A",
    "confidence": "High"
  }
}
```

Publish this schema to the team on Day 1. Frontend and AI/DevOps build against it.

---

## Phase 2 — Verification System Backend

- Add `score_history` table for tracking score changes over time
- Add `credential_verifications` table linking influencers to verified credentials
- Implement audit log on every score change (who/what/when)
- Multi-tenant support: `brands` table, scope all queries by brand_id
- API key authentication + rate limiting per brand

## Phase 3 — Knowledge Graph Backend

- Integrate Apache AGE (PostgreSQL graph extension) or migrate to Neo4j
- Build graph query layer: `GET /api/influencers/{id}/network`
- Endpoint for relationship discovery: `GET /api/influencers/{id}/cites`, `/cited-by`
- Async batch jobs for graph metric computation (PageRank, centrality)
- GraphQL layer for flexible graph traversal queries
