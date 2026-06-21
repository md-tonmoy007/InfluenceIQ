# Role 4: Pipeline Intelligence

This role owns the pipeline domain from search planning through influencer extraction, identity resolution, scoring, and safety classification.

## Mission

Turn campaign intent plus public web evidence into ranked, explainable influencer recommendations with traceable provenance and deterministic fallbacks.

## Owns

- Search query planning and result normalization in `backend/pipeline/tasks/search.py` and `backend/pipeline/content/search_providers.py`
- Fetching, crawl controls, readable-content extraction, provider adapters, and content contracts in `backend/pipeline/content/`
- Entity and signal extraction in `backend/pipeline/extraction/`
- Canonical identity resolution in `backend/pipeline/identity/`
- Heuristic and optional-model analysis in `backend/pipeline/analysis/`, `backend/pipeline/detection/`, and `backend/pipeline/model_classifiers.py`
- Score fusion, trust logic, versioning, and recommendation-ready output shaping in `backend/pipeline/fusion/`
- Synchronous pipeline orchestration logic in `backend/pipeline/orchestrator/pipeline.py`
- Optional ML adapters and experimental engines in `backend/ml/`

## Interfaces Consumed

- Campaign inputs and scoring weights from Backend API + Data
- Queue routing and worker runtime from Platform + Orchestration
- Redis event and state adapters from `backend/core/cache/` through Celery task bodies
- Database persistence targets defined in `backend/core/database/models.py`

## Interfaces Produced

- Celery task bodies in:
  - `backend/pipeline/tasks/search.py`
  - `backend/pipeline/tasks/crawl.py`
  - `backend/pipeline/tasks/extract.py`
  - `backend/pipeline/tasks/score.py`
- Candidate payloads passed from crawl/extraction to identity and scoring stages
- Event payloads such as `influencer.found` and `score.calculated` via `backend/pipeline/events/`
- Recommendation-ready score outputs with sub-scores, explanations, confidence, and provenance
- Persistable source and score records aligned to backend database models

## Queue Model

The current operational split is the canonical three-queue layout:

| Queue | Responsibility | Main task names |
| --- | --- | --- |
| `ai_agent_queue` | query generation and optional LLM-only decisions | `generate_queries`, `resolve_identity_llm`, `classify_brand_safety` |
| `scraping_queue` | search, fetch, crawl, readable content extraction | `execute_search`, `fetch_page`, `extract_content` |
| `scoring_queue` | influencer extraction, scoring, persistence-facing scoring work | `extract_influencers`, `score_influencer` |

Extraction is part of the scoring side operationally even though it lives in the broader pipeline domain.

## Key Workflows

- Generate campaign-specific queries with deterministic fallbacks when model-backed planning is unavailable.
- Normalize search results into source candidates with enough metadata for fetch, provenance, and ranking.
- Fetch and extract readable content, social links, and source evidence while preserving source URLs and status metadata.
- Extract influencer mentions, credentials, handles, titles, contact clues, and authority signals from source material.
- Resolve canonical identities across mentions and profile URLs before scoring.
- Compute engagement, credibility, sentiment, fake-signal, and brand-safety signals, then fuse them into final trust-oriented recommendation scores.
- Emit replay-safe progress and score events, while keeping raw sensitive contact details out of public event payloads.

## Durable Contracts

### Source And Provenance

- Every scoreable candidate must retain `source_url` or `source_urls`.
- Extracted source evidence must remain attributable when persisted to `crawl_sources`.
- Recommendation outputs must continue to map back to campaign and influencer records.

### Score Outputs

- Final outputs must preserve sub-scores, `final_score`, `confidence`, `grade`, `score_version`, and explanation/reason data.
- Low-evidence candidates must degrade confidence and caps deterministically rather than failing silently.
- Optional ML adapters may enrich results but must not break the deterministic baseline path.

### Event Safety

- Public score events are built through `backend/pipeline/events/`.
- Contact information is redacted before it enters the replayable WebSocket stream.

## Non-Goals

- Does not own FastAPI route design, response pagination policy, or WebSocket connection lifecycle.
- Does not own Docker, deployment, or queue scaling topology.
- Does not redefine database or Redis primitives that belong to shared infrastructure.

## Key Files And Directories

- `backend/pipeline/tasks/`
- `backend/pipeline/content/`
- `backend/pipeline/extraction/`
- `backend/pipeline/identity/`
- `backend/pipeline/analysis/`
- `backend/pipeline/detection/`
- `backend/pipeline/fusion/`
- `backend/pipeline/orchestrator/pipeline.py`
- `backend/pipeline/events/__init__.py`
- `backend/ml/`
- `backend/tests/pipeline/`
- `backend/tests/ml/`

## Handoff Contracts

- To Backend API + Data:
  - Persistable outputs must fit the campaigns, influencers, crawl sources, and influencer score models.
  - Event payloads must be safe for replay and presentation.
- To Frontend:
  - Recommendation outputs must stay explainable, attributable, and stable enough for UI mapping.
  - Event types and payload fields used by progress and shortlist views must remain intentional and documented.
- From Platform + Orchestration:
  - Queue names, retries, Redis availability, and worker startup must support the published task topology.
