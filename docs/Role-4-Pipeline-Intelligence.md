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

---

## Event Taxonomy

Every event that flows through Redis is constructed via a dataclass in `backend/pipeline/events/__init__.py`. The `event_type` string is passed to `publish_event(campaign_id, event_type, **payload)` as a positional argument. Events are replay-safe, PII-redacted (for score events), and versioned.

| event_type | Dataclass | Emitted By | Key Fields |
| --- | --- | --- | --- |
| `query.generation.completed` | `QueryGenerationCompleted` | `generate_queries` | `query_count`, `queries` |
| `search.executed` | `SearchExecuted` | `execute_search` | `query`, `index`, `result_count`, `crawl_source_ids` |
| `search.failed` | `SearchFailed` | `execute_search` | `query`, `index`, `error` |
| `page.fetched` | `PageFetched` | `fetch_page` | `crawl_source_id`, `url`, `status`, `cached` |
| `crawl.failed` | `CrawlFailed` | `_mark_failed` | `crawl_source_id`, `error` |
| `content.extracted` | `ContentExtracted` | `extract_content` | `crawl_source_id`, `url`, `title`, `social_links`, `metrics` |
| `influencer.found` | (raw dict) | `extract_influencers` | `crawl_source_id`, `url`, `new_influencer_ids`, `influencer_ids`, `mention_count` |
| `influencers.none` | `InfluencersNone` | `extract_influencers` | `crawl_source_id`, `url` |
| `identity.resolved` | `IdentityResolved` | `resolve_identity_llm` | `candidate_a`, `candidate_b`, `merge`, `confidence`, `reason`, `llm_used` |
| `identity.ambiguous` | `IdentityAmbiguous` | `resolve_identity_cluster` | `candidate_a`, `candidate_b`, `confidence`, `reason` |
| `identity.merged` | `IdentityMerged` | `resolve_identity_clusters` | `canonical_id`, `merged_from`, `confidence` |
| `score.calculated` | `ScoreCalculated` | `score_influencer` | `influencer_id`, `overall_fake_risk`, `detection_category`, `risk_category`, `final_score`, `grade`, `confidence`, `computed_at` |
| `brand_safety.flagged` | `BrandSafetyFlagged` | `classify_brand_safety` | `source_url`, `mention_label`, `influencer_id`, `flag_count`, `requires_llm_review`, `sample_flags` |
| `campaign.cancelled` | `CampaignCancelled` | `cancel_campaign` | `reason`, `influencer_count` |

> **Note:** The `score.calculated` event's `contact_info` field (when present) is redacted via SHA-256 truncation before publishing. Raw PII lives only on the `Influencer` ORM row.

## Optional ML Adapters

The deterministic pipeline can be enriched by optional ML adapters controlled by environment flags. All adapters are defined in `backend/pipeline/fusion/backends/ml_adapters.py` and wired through `backend/pipeline/fusion/components.py`. When all flags are off (the default), behavior is byte-for-byte identical to the all-heuristics path.

| Flag | Adapter | Effect | Model Version Bump |
| --- | --- | --- | --- |
| `ML_USE_SEMANTIC_V2` | `semantic_v2_score` | Replaces the heuristic spam/toxicity/AIGC average with a registry-driven `SemanticEngineV2` call | v2 |
| `ML_USE_BEHAVIORAL_V2` | `behavioral_v2_score` | Replaces the heuristic behavioral average with a calibrated `BehavioralEngine` call | v2 |
| `ML_USE_GRAPH_V2` | `graph_v2_score` | Inert in v1 — reserved for future GraphEdge extraction | v2 |
| `ML_USE_BOT_RINGS_V2` | `bot_rings_v2_score` | Inert in v1 — reserved for future GraphEdge extraction | v2 |
| `ML_USE_LLM_EXPLAINER` | `explain_via_llm` | Enriches the `score.calculated` event with an LLM-generated natural-language explanation | No bump (presentation layer) |
| `AI_AGENT_LLM_QUERY_PLANNING` | `_llm_generate_queries` | Uses the model registry's LLM backend to generate campaign-specific search queries | N/A (search phase) |
| `AI_AGENT_LLM_IDENTITY` | `resolve_identity_llm` | Routes ambiguous identity-resolution pairs through the LLM explainer | N/A (identity phase) |

When any scoring adapter fires (semantic, behavioral, graph, or bot-rings v2), the model version in the risk score payload bumps to `Role4-InfluenceScore-v2`. The all-heuristics path emits `Role4-InfluenceScore-v1` in the `model_version` field.

## Quickstart

**Entry point:** `backend.pipeline.orchestrator.pipeline.run_role4_pipeline(candidate, campaign)`

**Queue topology:** Three Celery queues — `ai_agent_queue`, `scraping_queue`, `scoring_queue` (documented in `backend/core/celery/roles.py` and `docker-compose.yml`).

**Test commands:**

```bash
# All pipeline tests (fast, mocked)
pytest backend/tests/pipeline/ -v

# ML smoke tests (fast, mocked)
pytest backend/tests/pipeline/test_ml_smoke.py -v
pytest backend/tests/pipeline/test_ml_adapters.py -v

# Query planning
pytest backend/tests/pipeline/test_query_planning.py -v

# Scoring contract
pytest backend/tests/pipeline/test_score_e2e.py -v
```

**Durable-contract assertions:**

| Contract | Test File | What It Asserts |
| --- | --- | --- |
| Final score in [0, 100] | `test_score_e2e.py` | `final_score` is in range |
| Model version present | `test_score_e2e.py` | `model_version` contains `Role4-InfluenceScore` |
| Sub-scores present | `test_score_e2e.py` | All 12 sub-score keys exist |
| Signal scores present | `test_score_e2e.py` | All expected signal-score keys exist |
| Source URLs non-empty | `test_score_e2e.py` | `source_urls` is a non-empty list |
| Positive reasons non-empty | `test_score_e2e.py` | At least one positive reason exists |
| Queue routing | `test_queue_routing.py` | Every task ships to its documented queue |
| Deterministic order | `test_stable_ordering.py` | Identical inputs produce identical outputs |
| PII redaction | `test_contact_info.py` | Contact info is SHA-256-hashed in score events |
| Sparse-data degradation | `test_renormalized_fusion.py` | Fewer than 3 sources applies cap + multiplier |
| Identity merge events | `test_identity_cluster.py` | Near-duplicates merge and emit `identity.merged` |
| Error taxonomy | `test_fetch_errors.py` | Every httpx exception maps to a `FetchErrorCode` |

**Cross-references:**

- API contracts: `docs/Role-3-Backend.md`
- Frontend event consumption: `docs/Role-2-Frontend.md`
- Architecture overview: `docs/architecture.md`
