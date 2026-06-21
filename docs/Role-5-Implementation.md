# Role 5 Implementation

Role 5 is implemented in `backend.pipeline/` and the Celery adapters
that fan work into it live in `app/tasks/score.py` and
`app/tasks/extract.py`. The published Celery contract in
`app/service_roles.py` is unchanged.

## Boundaries

- **Extraction** (`backend.pipeline/extraction/`) parses raw page
  text, optional HTML, supplied social links, credentials, titles,
  authority mentions, and context. spaCy PERSON NER is optional;
  missing spaCy or `en_core_web_sm` falls back to deterministic
  extraction.
- **Identity resolution** (`backend.pipeline/identity/`) uses
  normalized URL hashes, RapidFuzz-compatible name/username
  matching, and an ambiguous-pair handoff. It never calls an
  external LLM in v1.
- **Full graph analytics** remain outside Role 5. Local cluster
  evidence only produces `graph_proxy_score` and
  `bot_ring_signal_score`.
- **Celery adapters** are the only code that talks to Redis.
  The deterministic scorers are I/O-free; only
  `app/tasks/extract.py::extract_influencers` and
  `app/tasks/score.py::score_influencer` persist rows and emit
  events.

## Public entry points

- `backend.pipeline.orchestrator.pipeline.run_role5_pipeline(candidate, campaign)`
  returns `Role5PipelineResult` — the full role-5 output contract
  (detection, sub-scores, signal-scores, risk-score, grade, confidence,
  positive / negative reasons, contact_info, score_event).
- `backend.pipeline.identity.resolver.resolve_identity_clusters(candidates)`
  returns `canonical`, `ambiguous_pairs`, and `merge_events`.
- `backend.pipeline.extraction.entities.extract_influencer_mentions(page)`
  returns auditable mention records.
- `backend.pipeline.fusion.sub_scores.build_influencer_output(candidate, campaign)`
  returns the frontend / backend influencer contract.
- `backend.pipeline.fusion.sub_scores.build_sub_scores(candidate, campaign)`
  retains the legacy five-score view for existing consumers.

## Celery task bodies (Phase 3)

The 8 task bodies that drive the pipeline live in
`app/tasks/`. Their public function names match the queue name
in `app/service_roles.py`:

| Task                                       | Queue             | Body                                |
| ------------------------------------------ | ----------------- | ----------------------------------- |
| `backend.pipeline.tasks.search.generate_queries`         | `ai_agent_queue`  | `app/tasks/search.py`               |
| `backend.pipeline.tasks.search.execute_search`          | `scraping_queue`  | `app/tasks/search.py`               |
| `backend.pipeline.tasks.crawl.fetch_page`               | `scraping_queue`  | `app/tasks/crawl.py`                |
| `backend.pipeline.tasks.crawl.extract_content`          | `scraping_queue`  | `app/tasks/crawl.py`                |
| `backend.pipeline.tasks.extract.extract_influencers`    | `scoring_queue`   | `app/tasks/extract.py`              |
| `backend.pipeline.tasks.extract.resolve_identity_llm`   | `ai_agent_queue`  | `app/tasks/extract.py`              |
| `backend.pipeline.tasks.score.score_influencer`         | `scoring_queue`   | `app/tasks/score.py`                |
| `backend.pipeline.tasks.score.classify_brand_safety`    | `ai_agent_queue`  | `app/tasks/score.py`                |

`app/tasks/__init__.py::start_pipeline(campaign_id)` is the chain
entry point called from `app/api/campaigns.py`.

## Model Replacement

Every analyzer accepts feature dictionaries and has no hard
provider dependency. Model probabilities can be supplied by upstream
services. Fake-comment scoring blends `model_fake_probability` only
when present; otherwise it uses the documented deterministic
formula.

Optional API-backed model classifiers are also available for
production experiments:

| Env var                          | Default                       | Effect                                            |
| -------------------------------- | ----------------------------- | ------------------------------------------------- |
| `ROLE5_USE_MODEL_CLASSIFIERS`    | unset                         | Set to `1` to enable external model calls.        |
| `OPENAI_API_KEY`                 | unset                         | Required when API-backed classifiers are enabled.  |
| `ROLE5_MODEL_CLASSIFIER_MODEL`   | `OPENAI_JUDGE_MODEL` or `gpt-4o-mini` | Model used for Role-5 classification.     |
| `ROLE5_MODEL_CLASSIFIER_TIMEOUT` | `8`                           | Request timeout in seconds.                       |

The optional classifiers cover fake comments, suspicious followers,
bot behavior, brand safety, and sentiment quality. All calls fail
closed: if the model is disabled, the key is missing, the network
fails, or the response cannot be parsed, Role 5 returns the
deterministic heuristic score.

## Optional backend.ml v2 adapters

The v2 ML backends in `backend.ml/` are entirely optional and disabled
by default. They engage via the `UMGL_USE_*` env flags documented
in `backend.ml/README.md`. The adapter contract is in
`backend.pipeline/scoring/backends/umgl_ai_adapters.py`.

When the package is not installed, every adapter returns the
documented "no evidence" tuple and the orchestrator falls back to
the deterministic path. There is no behavior change between
"backend.ml not installed" and "backend.ml installed with all flags off".

## Testing

Run the full offline suite (no docker required):

```bash
make test-unit
```

This runs:

- `tests/test_role4_scraping.py` — the scraping contract
- `tests/test_role5.py` — the role-5 scoring contract
- `tests/test_celery_tasks.py` — Celery task chain under
  `CELERY_TASK_ALWAYS_EAGER=True`, with DB and Redis mocked
- `tests/test_app_smoke.py` — import-everything + route table +
  Celery task-routes contract
- `backend.pipeline/tests/` — every deterministic scorer, identity
  resolver, detection classifier, backend.ml adapter

The suite covers: five HTML fixtures, optional NER fallback,
extraction, identity passes, all fake-risk formulas, brand safety,
credibility, sentiment suppression, renormalization, trust caps,
explanations, output contracts, the Celery task chain wiring, and
the v2 adapter graceful-degradation contract.
