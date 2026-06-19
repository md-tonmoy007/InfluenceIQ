# Day 1 Contracts — Published

Authoritative contracts every role builds against. **Do not change without notifying the team.**

---

## 1. Redis Key Schema (Owner: AI/DevOps)

| Key Pattern                     | Type   | TTL         | Writer                           | Reader            |
| ------------------------------- | ------ | ----------- | -------------------------------- | ----------------- |
| `url_cache:{sha256(url)}`       | String | 48h         | Scraping                         | Scraping          |
| `pipeline_events:{campaign_id}` | List   | 1h          | All workers (via `emit_event`)   | Backend WebSocket |
| `pipeline_state:{campaign_id}`  | Hash   | 2h          | All workers (via `update_state`) | Backend REST      |
| `rate_limit:{domain}`           | String | 10s sliding | Scraping                         | Scraping          |
| `celery_task:{task_id}`         | String | 6h          | Celery internal                  | Celery internal   |

**Channels (pub/sub):**

- `campaign:{campaign_id}` — workers publish events; WebSocket server subscribes.

**Helper functions** (in `app/services/`):

- `emit_event(campaign_id, type, payload)` — appends to `pipeline_events:{id}` list AND publishes to `campaign:{id}` channel.
- `update_state(campaign_id, **fields)` — HSET on `pipeline_state:{id}`.

Workers **must not** write to Redis directly. Use these helpers.

---

## 2. Celery Task Signatures (Owner: AI/DevOps)

All tasks are in `platform/app/tasks/` and routed automatically via `app.celery_app` `task_routes`.

### search_queue

```python
generate_queries(campaign_id: str) -> list[str]
execute_search(campaign_id: str, query: str) -> list[dict]
    # returns: [{url, title, snippet, relevance_score}]
```

### crawl_queue

```python
fetch_page(campaign_id: str, url: str) -> dict
    # returns: {url, html, status, cached: bool, fetched_at}
extract_content(page: dict) -> dict
    # returns: {url, title, content, social_links: list[str], metadata: dict}
```

### extract_queue

```python
extract_influencers(campaign_id: str, page: dict) -> list[dict]
    # returns: list[InfluencerMention]  (see data model below)
resolve_identity_llm(candidate_a: dict, candidate_b: dict) -> dict
    # returns: {merge: bool, reason: str, confidence: float}
```

### score_queue

```python
classify_brand_safety(campaign_id: str, content: dict) -> dict
    # returns: {risks: dict[str, bool], reasons: list[str], source_url: str}
score_influencer(campaign_id: str, influencer_id: str, sub_scores: dict) -> dict
    # returns: {final_score, grade, confidence, score_version, computed_at, data_source_count}
```

### Task chaining (example)

```python
from celery import chain, group, chord

pipeline = chain(
    generate_queries.s(campaign_id),
    group(execute_search.s(campaign_id, q) for q in queries),
    group(fetch_page.s(campaign_id, url) for url in urls),
    chord(
        group(extract_influencers.s(campaign_id, page) for page in pages),
        score_influencer.s(campaign_id)
    ),
)
pipeline.apply_async()
```

---

## 3. WebSocket Event Schema (Owner: Backend — placeholder until Backend confirms)

```json
{
  "event_id": 42,
  "type": "score.calculated",
  "campaign_id": "uuid",
  "timestamp": "2026-05-21T10:30:00Z",
  "payload": {}
}
```

**Event types:**

- `query.generated` `{queries: [str]}`
- `url.discovered` `{url, title, relevance}`
- `url.cache_hit` `{url}`
- `page.scraped` `{url, status}`
- `page.rate_limited` `{url, retry_in}`
- `influencer.found` `{name, platform, source}`
- `identity.merged` `{canonical_id, merged_from}`
- `score.calculated` `{influencer_id, grade, confidence}`
- `pipeline.completed` `{total_influencers, duration_seconds}`

---

## 4. Influencer Data Model (Owner: Scoring — placeholder)

```json
{
  "influencer_id": "uuid",
  "canonical_name": "Dr Sarah Tan",
  "platforms": {
    "instagram": "@drsarahtan",
    "youtube": "youtube.com/sarahtan"
  },
  "credentials": ["MD", "Certified Nutritionist"],
  "mentions": [
    { "name": "Sarah Tan MD", "source_url": "https://...", "context": "..." }
  ],
  "sub_scores": {
    "relevance": 85,
    "credibility": 78,
    "engagement": 72,
    "sentiment": 80,
    "brand_safety": 95
  },
  "confidence": "High",
  "data_source_count": 7
}
```

---

## 5. Environment & Secrets

See `.env.example` at repo root. Every contributor copies it to `.env` and fills in API keys locally. Required keys:

- LLMs: `MOONSHOT_API_KEY` (Kimi K2), `GOOGLE_API_KEY` (Gemini 2.5 Flash), `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`
- Search: `BRAVE_SEARCH_API_KEY`, `OPENSERP_API_KEY`
- Infra: `DATABASE_URL`, `REDIS_URL`, `QDRANT_URL` (defaults work with docker-compose)

---

## 6. Token Budgets (hard caps per task)

| Task                    | Max tokens |
| ----------------------- | ---------- |
| `generate_queries`      | 2000       |
| `classify_brand_safety` | 800        |
| `resolve_identity_llm`  | 400        |
| `score_explain`         | 1500       |

Enforced in `app/llm/budget.py` (Day 2 deliverable).

---

## How to run

```bash
cp .env.example .env
# fill in API keys
docker compose up -d
curl http://localhost:8000/health
open http://localhost:5555/flower    # Celery monitoring
```
