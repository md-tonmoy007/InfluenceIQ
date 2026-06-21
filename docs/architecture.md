# InfluenceIQ Architecture

InfluenceIQ is an AI-powered, trust-aware influencer discovery platform. A brand submits a campaign brief, the system discovers public creator signals, resolves candidate influencer identities, scores each candidate for fit and risk, and returns ranked recommendations with explainable evidence.

This document is the canonical architecture reference for the docs folder. It describes the target architecture and the contracts the application should converge on.

## Product Purpose

Influencer discovery should answer "who should this brand trust?" rather than only "who is popular?" The platform therefore optimizes for:

- campaign-specific relevance instead of generic popularity
- source-backed credibility and credential signals
- organic engagement quality over raw follower counts
- sentiment and audience trust indicators
- explicit brand-safety risk flags
- explainable recommendations that cite source provenance

## Architecture Principles

- Build as a modular monolith: one backend codebase with clear module boundaries, not premature microservices.
- Keep the frontend and backend on one canonical contract. Derive client and server types from that contract where possible.
- Treat source provenance as first-class data. One source can mention multiple influencers, and one influencer can be supported by many sources.
- Store scoring runs as versioned, auditable records instead of transient UI payloads.
- Prefer deterministic fallbacks for query generation, search parsing, extraction, safety checks, and scoring. LLM and ML adapters are optional replaceable engines.
- Update pipeline state atomically and use explicit terminal campaign states.
- Keep worker separation at three operational queues until measured load proves that a fourth extraction queue is needed.

## Runtime Topology

```text
Browser dashboard
      |
      | REST + WebSocket
      v
Next.js frontend
      |
      | /api proxy or direct API calls
      v
FastAPI backend
      |
      +-- PostgreSQL: durable campaigns, influencers, provenance, scores, flags
      +-- Redis: Celery broker, pipeline state, event replay, caches, rate limits
      +-- Celery workers
      |     +-- ai_agent_queue: query generation and optional LLM decisions
      |     +-- scraping_queue: search, fetch, crawl, and content extraction
      |     +-- scoring_queue: identity extraction, scoring, and safety persistence
      +-- Flower: Celery operations dashboard
      +-- Optional engines
            +-- Qdrant or pgvector for embeddings and semantic retrieval
            +-- ML or LLM adapters for advanced risk, identity, and explanation work
```

The FastAPI app owns synchronous API contracts and campaign orchestration. Celery owns long-running work. Redis connects the API and workers through queueing, low-latency state, and replayable event streams. PostgreSQL is the source of truth for all durable business data.

## Campaign Flow

```text
POST /api/campaigns
      |
      +-- create campaign row with brief, weights, and lifecycle state
      +-- initialize Redis pipeline state
      +-- dispatch root pipeline task
             |
             v
ai_agent_queue
      generate campaign search queries
             |
             v
scraping_queue
      execute search, fetch pages, extract readable content,
      record source provenance, and emit progress events
             |
             v
scoring_queue
      extract influencer mentions, resolve canonical identities,
      run score computation, persist score runs and safety flags
             |
             v
FastAPI + Redis event stream
      expose state, replayable WebSocket events, and ranked recommendations
```

Campaigns should move through explicit lifecycle states such as `queued`, `running`, `partial`, `completed`, `failed`, and `cancelled`. A failed task should not erase useful work already persisted; the API can return partial recommendations with a clear campaign state and error reason.

## Backend Boundaries

### API Layer

The API layer exposes campaign creation, state polling, recommendation retrieval, influencer profile retrieval, health checks, and WebSocket streams. It validates requests, starts pipeline work, reads durable data from PostgreSQL, reads fast state from Redis, and translates backend models into public response contracts.

### Core Infrastructure

Core infrastructure owns configuration, logging, database sessions, migrations, Redis clients, Celery app construction, task routing, cache helpers, event logging, and pipeline-state primitives. Shared infrastructure should not depend on campaign-specific scoring logic.

### Pipeline Domain

The pipeline domain owns search query planning, search result normalization, URL fetching, content extraction, influencer mention extraction, identity resolution, score computation, safety classification, and recommendation ranking. Pipeline functions should keep deterministic implementations available even when optional LLM or ML adapters are enabled.

### Workers

Workers are thin Celery entrypoints that import task modules for their assigned queue. Queue ownership is operational:

| Queue            | Responsibility                                                                        | Scaling driver                         |
| ---------------- | ------------------------------------------------------------------------------------- | -------------------------------------- |
| `ai_agent_queue` | query planning, optional LLM identity decisions, optional LLM safety/explanation work | external model latency and rate limits |
| `scraping_queue` | search calls, page fetches, crawl depth control, content extraction                   | network I/O and target-site throttling |
| `scoring_queue`  | influencer extraction, identity persistence, scoring, safety flag persistence         | CPU-bound scoring and database writes  |

### Optional ML

Optional ML modules can improve semantic matching, fake-engagement detection, graph features, or explanations. They must be adapter-driven so the deterministic pipeline still works when heavy dependencies or external providers are unavailable.

## Frontend Responsibilities

The frontend is the brand-facing workflow surface. It should:

- submit campaign briefs and scoring preferences
- render campaign state from REST and WebSocket events
- reconnect to the WebSocket stream using the last seen event id
- display ranked recommendations, source-backed explanations, and brand-safety warnings
- fetch canonical influencer profiles on demand
- treat the API contract as the source of truth, avoiding duplicated business rules in the client

The frontend should be resilient to partial data. While a campaign is running, it can show progress and any recommendations already computed. Once a terminal state arrives, it should stop expecting further pipeline events unless the campaign is explicitly rerun.

## Public API Contracts

### REST

`POST /api/campaigns`

Starts a campaign and returns the campaign identity plus initial state.

```json
{
  "campaign_id": "uuid",
  "state": "queued",
  "created_at": "2026-06-21T00:00:00Z"
}
```

`GET /api/campaigns/{id}`

Returns campaign metadata, brief fields, scoring weights, lifecycle state, timestamps, and any terminal error summary.

`GET /api/campaigns/{id}/state`

Returns fast pipeline state from Redis or a database fallback. This endpoint is the REST fallback for clients that cannot maintain a WebSocket.

```json
{
  "campaign_id": "uuid",
  "state": "running",
  "phase": "scoring",
  "urls_discovered": 47,
  "urls_processed": 31,
  "influencers_found": 12,
  "scores_computed": 8,
  "last_event_id": 42
}
```

`GET /api/campaigns/{id}/influencers`

Returns ranked recommendations for a campaign. Results should be sortable and filterable by platform, niche, region, grade, and follower band.

`GET /api/influencers/{id}`

Returns the canonical influencer profile: identity, platform handles, source provenance, latest campaign-specific scores, score history summary, credential evidence, and safety flags.

### WebSocket

`/ws/campaign/{campaign_id}?last_event_id=N`

The server replays events with `event_id > N` from `pipeline_events:{campaign_id}`, then attaches the connection to the live stream.

All events use a stable envelope:

```json
{
  "event_id": 42,
  "type": "score.calculated",
  "campaign_id": "uuid",
  "timestamp": "2026-06-21T00:00:00Z",
  "payload": {
    "influencer_id": "uuid",
    "final_score": 87.5,
    "grade": "A",
    "confidence": "high"
  }
}
```

Common event types include `campaign.started`, `query.generated`, `search.executed`, `source.fetched`, `content.extracted`, `influencer.found`, `identity.resolved`, `score.calculated`, `brand_safety.flagged`, `campaign.completed`, and `campaign.failed`.

## Data Architecture

### Campaigns

Campaigns own the brand brief, industry, audience, platform preferences, scoring weights, lifecycle state, timestamps, and terminal error information. They are the root for pipeline state and campaign-specific recommendation views.

### Influencers

Influencers are canonical creator identities. They store normalized names, known handles, profile URLs, topic metadata, and merge metadata. They should not duplicate every source mention inline; provenance belongs in dedicated source and attribution tables.

### Sources And Provenance

Sources represent discovered URLs, search results, fetched pages, extracted text, snippets, metadata, fetch status, and cache information. Source-to-influencer attribution is many-to-many because one article can mention multiple creators and one creator can appear across many sources. Attribution records should preserve what was observed, where it was observed, and which extraction method produced it.

### Score Runs

Score runs are append-only records linked to a campaign and influencer. Each run stores sub-scores, final score, grade, confidence, score version, scoring weights, source counts, explanation payloads, and `computed_at`. New formulas create new score versions rather than overwriting history.

### Brand-Safety Flags

Brand-safety flags preserve campaign linkage, influencer linkage, source URL, risk type, severity, reason, detection method, and timestamp. The platform should warn and explain; business rules decide whether a flag excludes a recommendation.

### Credential Verification

Credential evidence should be stored separately from influencer identity. Evidence can include source URL, credential type, extracted claim, verifier, confidence, and review state. This keeps professional credibility auditable and allows future human review.

## Scoring Architecture

The recommendation score combines normalized sub-scores:

- relevance: fit between campaign brief and influencer topics
- credibility: professional authority, credentials, and authoritative mentions
- engagement quality: organic interaction quality and fake-engagement risk
- sentiment: audience trust, toxicity, and positive/negative response patterns
- brand safety: risk-adjusted safety score where higher is safer
- confidence: data coverage, provenance quality, and agreement between signals

Default weighting can start with relevance and credibility as the strongest components, followed by engagement quality, sentiment, and brand safety. Campaigns may override weights, but every score run must persist the exact weights used.

Low-data candidates should be capped or penalized through confidence rules instead of receiving extreme scores from sparse evidence. Explanations should cite the source records and scoring version that produced them.

## Async Processing Model

Celery tasks should be idempotent at the campaign/source/influencer boundary. Re-running a task should update the same durable records or append a clearly versioned run, not create untraceable duplicates.

Recommended queue routing:

- `ai_agent_queue`: deterministic query planning first, optional LLM query expansion, optional LLM identity resolution, optional LLM safety classification, optional explanation generation
- `scraping_queue`: search-provider calls, URL deduplication, cache checks, fetches, crawl-depth control, content extraction, rate limiting
- `scoring_queue`: mention extraction, canonical identity writes, source attribution writes, score runs, safety flag persistence, recommendation ranking updates

The scraping queue remains broad by design. Add a separate extraction queue only if measured throughput shows content extraction blocking fetch work in production.

## Real-Time Events And Replay

Redis stores two related views of progress:

- `pipeline_state:{campaign_id}` as a hash for fast polling
- `pipeline_events:{campaign_id}` as an ordered event log for WebSocket replay

Each event receives a monotonically increasing `event_id` per campaign. Workers append events to the Redis replay log and publish them to the campaign live channel. The WebSocket handler first replays missed events, then streams new ones. Event logs can use a TTL, but durable business results must already be in PostgreSQL.

Pipeline-state updates should be atomic. Counts, phase changes, and terminal states should not be emitted in conflicting order.

## Observability

The target system should expose:

- `GET /health` for database, Redis, and worker health
- queue depth and worker count visibility through Flower and health checks
- structured logs from API and task workers with campaign id and task id
- task retry and failure counters
- event replay diagnostics, including last event id and replay length
- scoring version and adapter metadata for recommendation auditability

## Security

- Treat campaign input and crawled content as untrusted data.
- Do not execute fetched HTML; parse and extract only.
- Store provider keys and model credentials in environment-managed secrets.
- Keep CORS restricted to known frontend origins.
- Rate-limit external fetches by domain and respect provider quotas.
- Avoid sending raw sensitive credentials or secret values through WebSocket payloads.
- Preserve source URLs and detection reasons for auditability, but avoid exposing private operational metadata to public clients.

## Deployment

The production deployment can remain simple:

- Next.js frontend on a static or Node-capable frontend host
- FastAPI backend as the API service
- separate Celery worker processes or containers for the three queues
- managed PostgreSQL
- managed Redis
- Flower restricted to operators
- optional Qdrant, pgvector, or ML services enabled only when needed

The backend and workers can share the same application image. Runtime behavior should be selected by process command and environment variables rather than by building divergent images.

## Future Expansion

Future architecture can add:

- multi-tenant organizations and role-based access
- human review workflows for credential and safety evidence
- influencer score trend history
- graph-based relationship and citation analysis
- richer vector search and semantic campaign matching
- provider-specific social APIs where legally and operationally viable
- model evaluation datasets for fake-engagement and credibility scoring

These additions should preserve the same core boundaries: canonical API contracts, durable provenance, versioned score runs, deterministic fallbacks, and replayable campaign events.
