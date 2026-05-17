# Role 1: AI Orchestration + DevOps Lead

**Owner:** Team Lead (you)
**Architecture Sections Owned:** 2, 6, 14, 15, 16, 20, 21, 22

This is the critical path of the system. You own everything that makes the platform intelligent, runnable, and observable.

---

## Responsibilities

- Docker Compose environment (FastAPI + Celery + Redis + PostgreSQL)
- Celery configuration: 4 queues (search, crawl, extract, score) with retry policy
- LLM integrations: query generation, brand safety classifier, identity resolution LLM pass
- Trust scoring engine: normalization, weighted formula, score versioning
- Flower monitoring + `/health` endpoint
- Redis key design (URL cache, pipeline state, event log, rate limit counters)
- Deployment to Railway/Render

---

## 7-Day Todo List

### Day 1 — Foundation

- [ ] Create `docker-compose.yml` with FastAPI, Redis, PostgreSQL services
- [ ] Define Celery app config (`celery_app.py`) with 4 task routes
- [ ] Document Redis key schema (publish to team Slack/doc):
  - `url_cache:{sha256}` — 48h TTL
  - `pipeline_events:{campaign_id}` — 1h TTL
  - `pipeline_state:{campaign_id}` — 2h TTL
  - `rate_limit:{domain}` — 10s TTL
- [ ] Set up `.env.example` with all required keys (OpenAI/Anthropic, Brave, OpenSerp)
- [ ] Publish Celery task signature contracts to backend + scraping engineers

### Day 2 — LLM Skeleton + Worker Pool

- [ ] Write query generation prompt + LLM client wrapper
- [ ] Define worker startup scripts for each queue (concurrency: search=2, crawl=8, extract=4, score=2)
- [ ] Wire Flower into Docker Compose (`/flower` endpoint)
- [ ] Test: trigger a dummy Celery task from FastAPI, confirm it lands in correct queue
- [ ] Set hard LLM token budget per task type and document it

### Day 3 — Core LLM Tasks

- [ ] Implement `generate_queries` Celery task (campaign → search queries)
- [ ] Implement `classify_brand_safety` task (content → risk flags + reason)
- [ ] Implement `resolve_identity_llm` task (Pass 3 of identity resolution)
- [ ] Add Celery retry decorators with exponential backoff to all tasks
- [ ] Verify task chaining works (`chain()` and `chord()` primitives)

### Day 4 — Scoring Engine

- [ ] Implement sub-score normalization function (any raw input → [0, 100])
- [ ] Implement weighted final score formula with brand-customizable weights
- [ ] Add confidence penalty for low-data influencers (cap at 70 if <3 sources)
- [ ] Implement score versioning: store `score_version`, `computed_at`, `data_source_count`
- [ ] Write `score_influencer` Celery task that takes all sub-scores → final grade

### Day 5 — Integration + Monitoring

- [ ] Wire end-to-end pipeline: trigger campaign → all 4 queues fire in sequence
- [ ] Implement `/health` endpoint (queue depths, worker counts, DB/Redis status)
- [ ] Verify Flower shows all queues, workers, and task states correctly
- [ ] Add structured logging to all Celery tasks (campaign_id, task_id, duration)
- [ ] Pipeline state hash updates correctly across all phases

### Day 6 — Hardening + Deployment

- [ ] Deploy to Railway/Render (FastAPI + Celery workers as separate services)
- [ ] Configure managed Redis + PostgreSQL
- [ ] Run 3 full campaigns end-to-end and fix failures
- [ ] Add alerting thresholds (queue depth > 100, failure rate > 10%)
- [ ] Verify partial results return when pipeline fails mid-run

### Day 7 — Demo Prep

- [ ] Pre-run 2–3 demo campaigns, verify cached results in DB
- [ ] Confirm Flower dashboard is presentable (clean state, no error spam)
- [ ] Test rollback plan: if live demo fails, fallback to cached results
- [ ] Help teammates with last-minute LLM tweaks (prompts, edge cases)
- [ ] Final smoke test: full pipeline runs in under 90 seconds on demo query

---

## Key Files You Own

```
backend/
├── celery_app.py
├── tasks/
│   ├── search.py
│   ├── extract.py        (LLM portions)
│   └── score.py
├── llm/
│   ├── client.py
│   ├── prompts/
│   └── budget.py
├── scoring/
│   ├── normalize.py
│   ├── formula.py
│   └── versioning.py
docker-compose.yml
flower.config.py
.env.example
```

---

## Phase 2 — Verification System

- Integrate credential verification APIs (LinkedIn API, academic databases)
- Train lightweight ML classifier for fraud detection (replace heuristic)
- Add background re-scoring job (Celery beat) to refresh stale influencer scores weekly
- Expand LLM prompts to extract claimed credentials with confidence scores
- Add cost/quota tracking dashboard per campaign

## Phase 3 — Knowledge Graph

- Build graph embedding pipeline (Node2Vec or GraphSAGE) for influencer-relationship vectors
- Migrate scoring formula to graph-aware (trust propagation through network)
- Set up vector recommendation engine using pgvector + influencer embeddings
- Orchestrate batch graph computation jobs via Celery beat
- Multi-region worker deployment for scale
