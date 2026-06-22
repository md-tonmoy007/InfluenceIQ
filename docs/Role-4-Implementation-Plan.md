# Role 4 Implementation Plan — Pipeline Intelligence (End-to-End)

> Status: planning document derived from `docs/Role-4-Pipeline-Intelligence.md`
> and a full survey of `backend/pipeline/`, `backend/ml/`, `backend/core/`,
> `backend/tests/`, and `docker-compose.yml`. Treat every "Action" item below
> as a discrete unit of work with its own branch / PR / test set.

---

## 0. TL;DR

Role 4 owns the influence-discovery pipeline that converts a campaign into a
ranked, explainable shortlist of influencers. The repository already contains
a working "Role 5" pipeline (the v1 code paths in `backend/pipeline/` and
`backend/ml/`) that satisfies **most** of the contracts described in the
Role-4 charter. The remaining work is therefore not greenfield — it is
**consolidation, gap-closure, hardening, and contract alignment**.

This plan is organised in 9 phases. Each phase lists:

* the **goal** (what is being delivered)
* the **current state** (what is already in the repo and verified by tests)
* the **gaps** (what still has to be built or hardened)
* the **actions** (concrete steps, file paths, and acceptance criteria)
* the **verification** (tests / commands that prove the work is done)

The phases are roughly sequential but phases 6-8 can be parallelised across
multiple engineers.

---

## 1. Current-State Survey (what already exists)

The following modules are already implemented and covered by tests under
`backend/tests/pipeline/`:

| Module                                              | Status | Verified by                                    |
| --------------------------------------------------- | ------ | ---------------------------------------------- |
| `backend/pipeline/content/fetcher.py` + providers   | ✅      | `test_role4_scraping.py`                       |
| `backend/pipeline/content/content_extractor.py`    | ✅      | `test_role4_scraping.py`                       |
| `backend/pipeline/content/search_providers.py`      | ✅      | `test_role4_scraping.py`                       |
| `backend/pipeline/extraction/entities.py`           | ✅      | `test_extraction.py`, `test_role4_scraping.py` |
| `backend/pipeline/extraction/contact_info.py`       | ✅      | `test_contact_info.py`                         |
| `backend/pipeline/extraction/credentials.py`        | ✅      | `test_extraction.py`                           |
| `backend/pipeline/extraction/handles.py`            | ✅      | `test_extraction.py`                           |
| `backend/pipeline/extraction/social_urls.py`        | ✅      | `test_extraction.py`                           |
| `backend/pipeline/identity/canonical.py`            | ✅      | `test_identity.py`                             |
| `backend/pipeline/identity/fuzzy_match.py`          | ✅      | `test_identity.py`                             |
| `backend/pipeline/identity/url_match.py`            | ✅      | `test_identity.py`                             |
| `backend/pipeline/identity/resolver.py`             | ✅      | `test_identity.py`                             |
| `backend/pipeline/analysis/*.py` (12 files)         | ✅      | per-detector test files                        |
| `backend/pipeline/detection/*.py` (6 files)         | ✅      | `test_detection.py`                            |
| `backend/pipeline/fusion/components.py`             | ✅      | `test_renormalized_fusion.py`                  |
| `backend/pipeline/fusion/fusion.py`                | ✅      | `test_renormalized_fusion.py`                  |
| `backend/pipeline/fusion/sub_scores.py`             | ✅      | `test_scoring.py`                              |
| `backend/pipeline/fusion/trust.py`                  | ✅      | `test_role5.py`                                |
| `backend/pipeline/fusion/versioning.py`             | ✅      | `test_renormalized_fusion.py`                  |
| `backend/pipeline/fusion/backends/ml_adapters.py`   | ✅      | `test_ml_adapters.py`, `test_ml_smoke.py`      |
| `backend/pipeline/orchestrator/pipeline.py`         | ✅      | `test_orchestrator.py`                         |
| `backend/pipeline/events/__init__.py`               | ✅      | `test_role5.py` (event payload assertions)     |
| `backend/pipeline/tasks/search.py`                  | ✅      | `test_celery_tasks.py`                         |
| `backend/pipeline/tasks/crawl.py`                   | ✅      | `test_celery_tasks.py`                         |
| `backend/pipeline/tasks/extract.py`                 | ✅      | `test_celery_tasks.py`                         |
| `backend/pipeline/tasks/score.py`                   | ✅      | `test_celery_tasks.py`, `test_role5.py`        |
| `backend/pipeline/tasks/orchestrator.py`            | ✅      | `test_celery_tasks.py`                         |
| `backend/core/celery/roles.py` (queue routing)      | ✅      | covered indirectly by `test_celery_tasks.py`   |
| `backend/ml/*` (registry, semantic, behavioral, …)  | ✅ (stubs) | `test_ml_smoke.py`                          |

**Conclusion**: the v1 deterministic pipeline is in production shape. The
Role-4 charter is therefore mostly a **renaming + consolidation + small-gap
exercise**, not a from-scratch build. The next sections identify the
remaining gaps and the work needed to bring the codebase into a state that
a reviewer can read as "Role 4 implemented end to end".

---

## 2. Repository Findings the Plan Must Address

The Role-4 charter (`docs/Role-4-Pipeline-Intelligence.md`) refers to "Role 5"
internals repeatedly because the v1 implementation was already shipped under
the **Role 5** nomenclature. The plan must therefore:

1. **Rename the public surface** so the codebase matches the Role-4 charter
   (e.g., `Role5PipelineResult` → `Role4PipelineResult`,
   `backend.pipeline.orchestrator.pipeline.run_role5_pipeline` →
   `run_role4_pipeline`, `Role5-FakeDetectionScore-v1` →
   `Role4-InfluenceScore-v1`). The internal symbols (heuristics, detectors,
   sub-scorers) keep their names; only the **public entry points and the
   model-version string** change.
2. **Add the missing coverage** that the Role-4 doc explicitly calls out:
   * LLM-backed query generation as an optional path (currently only
     deterministic).
   * Identity-cluster fan-out that produces `identity.merged` events at
     the campaign level (the resolver already supports it but the Celery
     adapter does not call it).
   * A documented event taxonomy that the frontend can rely on.
3. **Tighten the durable contracts**: ensure every scored influencer row has
   `source_url` / `source_urls`, `score_version`, sub-scores, and a
   non-empty explanation. These are already enforced in code but should be
   covered by tests that fail loudly when a future refactor breaks them.
4. **Wire ML adapters** behind the existing flags so the optional path is
   exercised in CI smoke tests (`test_ml_smoke.py`).

---

## 3. Phase Plan

### Phase 1 — Alignment & Renaming (1 day)

**Goal**: make the public surface match `docs/Role-4-Pipeline-Intelligence.md`
without breaking the existing tests.

**Current state**:

* `backend/pipeline/orchestrator/pipeline.py` exports
  `run_role5_pipeline`, `Role5PipelineResult`, `trust_grade_to_confidence`.
* `backend/pipeline/fusion/versioning.py` exports
  `MODEL_VERSION = "Role5-FakeDetectionScore-v1"` plus the v2 alias.
* `backend/pipeline/events/__init__.py` documents "Pipeline 19" and refers
  to the role-5 spec.
* Celery task names are already role-neutral
  (`backend.pipeline.tasks.search.generate_queries` etc.) — keep as-is.

**Gaps**:

* Public symbol names still reference Role 5.
* The Role-4 doc describes the orchestrator as owning
  `backend/pipeline/orchestrator/pipeline.py` — the docstring should match.
* Model-version constants and the version emitted in score events need to
  point to the Role-4 string.

**Actions**:

1. **Add role-4 public symbols as aliases** (do **not** delete role-5 names
   — both the API layer and tests still import them):
   * In `backend/pipeline/orchestrator/pipeline.py` add
     `Role4PipelineResult = Role5PipelineResult` and
     `run_role4_pipeline = run_role5_pipeline` plus a deprecation comment
     that points at the Role-4 charter.
   * In `backend/pipeline/fusion/versioning.py` add
     `MODEL_VERSION_ROLE4: str = "Role4-InfluenceScore-v1"` and a helper
     `role4_version_for(...)` mirroring `model_version_for(...)`.
2. **Update the orchestrator docstring** to say it implements the
   role-4 pipeline as defined in `docs/Role-4-Pipeline-Intelligence.md`.
3. **Emit the Role-4 version** in the score event payload. The Celery task
   `score_influencer` writes `score_row.score_version`; switch the default
   to `MODEL_VERSION_ROLE4` while keeping `Role5-FakeSignal-v1` as an alias
   in `risk_score["model_version_v1_alias"]` for backwards compatibility.
4. **Update frontend-facing constants**: any code that serialises the
   model version into API responses should still expose both names
   (`model_version` = role-4 string, `model_version_v1_alias` = role-5 string).

**Verification**:

* `pytest backend/tests/pipeline/test_orchestrator.py -k role4` passes.
* `pytest backend/tests/pipeline/test_role5.py` still passes (legacy).
* `pytest backend/tests/pipeline/test_renormalized_fusion.py` confirms both
  `MODEL_VERSION` and the new `MODEL_VERSION_ROLE4` are emitted.
* `rg "Role5" backend/pipeline/` shows the legacy string only inside
  `MODEL_VERSION_ALIAS` and the v1 alias field.

---

### Phase 2 — Queue Topology & Celery Wiring (½ day)

**Goal**: confirm the three-queue split described in the Role-4 doc is
the runtime truth, and that every task ships with the right queue.

**Current state** (from `backend/core/celery/roles.py`):

```
ai_agent_queue    : generate_queries, resolve_identity_llm, classify_brand_safety
scraping_queue    : execute_search, fetch_page, extract_content
scoring_queue     : extract_influencers, score_influencer
```

**Gaps**:

* `docker-compose.yml` may not yet declare the three queues as separate
  worker services. Verify and, if missing, add one service per queue.
* `pytest backend/tests/pipeline/test_celery_tasks.py` runs all tasks in
  eager mode without asserting queue routing. Add a small test that
  patches `app.send_task` and confirms each task is sent to the documented
  queue.

**Actions**:

1. Audit `docker-compose.yml` and add / fix:
   * `celery-ai-agent`     → `-Q ai_agent_queue`
   * `celery-scraping`     → `-Q scraping_queue`
   * `celery-scoring`      → `-Q scoring_queue`
   * Existing single-worker service is renamed `celery-all` (still
     subscribes to all three queues for local dev convenience).
2. Add `test_queue_routing.py` under `backend/tests/pipeline/` that
   imports `backend.core.celery.roles.TASK_QUEUE_BY_NAME` and asserts each
   task maps to the queue the Role-4 doc lists.
3. Document the queue ownership in `docs/architecture.md` (one paragraph).

**Verification**:

* `docker compose config --services` lists the new services.
* `pytest backend/tests/pipeline/test_queue_routing.py -v` passes.
* `docker compose up celery-ai-agent celery-scraping celery-scoring` boots
  cleanly and consumes the right tasks.

---

### Phase 3 — Query Planning (1 day)

**Goal**: the `generate_queries` task must produce 3–5 high-quality,
campaign-specific queries with a deterministic fallback when the LLM path
is disabled.

**Current state** (`backend/pipeline/tasks/search.py::generate_queries`):

* Builds queries deterministically from `product`, `niche`, `goals`,
  `target_audience`, `preferred_platforms`.
* 3-5 queries; tagged with platform hints (e.g., `… youtube`).
* Always fans out to `execute_search.delay(...)`.
* No LLM path today.

**Gaps**:

* No optional LLM path.
* No de-duplication of near-identical queries.
* No per-platform diversification (a campaign asking for "fitness
  creators" on YouTube should produce a YouTube-specific query, but
  Instagram-only campaigns should not get a YouTube tag).

**Actions**:

1. Add an optional LLM path in `generate_queries`:
   * Reads `AI_AGENT_LLM_QUERY_PLANNING=1` env flag.
   * Calls `backend.ml.llm_explainer.LLMExplainer` (already implemented)
     with a strict JSON schema (`{"queries": [...]}`).
   * On error / empty result / flag off, falls back to
     `_build_query_set`.
2. Add a small `dedupe_queries()` helper that drops queries whose
   normalised token-set Jaccard similarity ≥ 0.8.
3. Add per-platform diversification: if `preferred_platforms` is set,
   ensure at least one query targets each preferred platform.
4. Tests:
   * `test_generate_queries_deterministic()` — covers current behaviour.
   * `test_generate_queries_dedupes_near_duplicates()`.
   * `test_generate_queries_prefers_platforms()` — every preferred
     platform appears in at least one query.
   * `test_generate_queries_llm_path_with_flag()` — patches
     `classify_with_model` (or the LLM explainer) and asserts LLM
     output is preferred when flag is on.

**Verification**: `pytest backend/tests/pipeline/test_celery_tasks.py -k query`
passes; new tests in `backend/tests/pipeline/test_query_planning.py` pass.

---

### Phase 4 — Search, Fetch, Extraction (1 day)

**Goal**: every URL discovered by the search phase is fetched, parsed,
and converted into a role-4-ready content dict, **or** is marked failed
with a deterministic reason. Caching, rate limiting, and per-platform
adapters all behave consistently.

**Current state**:

* `search_web(query, limit)` falls back to real discovery targets when
  `BRAVE_SEARCH_API_KEY` / `OPENSERP_URL` are empty.
* `fetch_url(url)` routes YouTube / Instagram / TikTok / X to platform
  providers; falls back to a generic HTML fetcher for everything else.
* `extract_role5_content(page)` produces a content dict with
  `role5_candidate` payload that the orchestrator consumes.
* Cache, rate limiter, content contracts all in place.

**Gaps**:

* No retry budget / breaker when a provider consistently fails.
* No taxonomy for `fetch_error` codes (today only the raw exception
  string is persisted).
* `extract_role5_content` builds a `role5_candidate` dict — rename the
  key to `role4_candidate` while keeping the old key as an alias so the
  tests pass.

**Actions**:

1. **Failure taxonomy**: add `backend/pipeline/content/errors.py` with
   the enum `FetchErrorCode = {TIMEOUT, DNS, SSL, STATUS_4XX, STATUS_5XX,
   PARSE_ERROR, RATE_LIMITED, BLOCKED, PROVIDER_DOWN}`. Map exceptions
   to codes inside `fetcher.fetch_url()` and persist
   `source.error_message = f"{code.name}: {detail}"`.
2. **Per-provider circuit breaker**: keep a Redis-backed counter
   (`role4:provider_fail:{provider}`) in `backend/core/cache/`. After 5
   failures in 60 s, switch the provider off for 5 minutes and route
   calls to the generic fetcher.
3. **Candidate payload rename**: in
   `backend/pipeline/content/content_extractor.py` write both
   `role5_candidate` (legacy) and `role4_candidate` (new) keys from the
   same dict. After one release cycle, drop the legacy key.
4. **Tests**:
   * `test_fetch_error_taxonomy.py` — every documented exception maps
     to a `FetchErrorCode`.
   * `test_provider_circuit_breaker.py` — six consecutive failures
     cause the breaker to open, and a follow-up call skips the provider.
   * `test_extract_role4_candidate_key.py` — content dict contains both
     candidate keys for one release.

**Verification**:

* `pytest backend/tests/pipeline/test_role4_scraping.py -v` passes.
* New tests under `backend/tests/pipeline/test_fetch_errors.py` and
  `backend/tests/pipeline/test_circuit_breaker.py` pass.
* Manual: temporarily block a provider in dev, observe breaker open
  and `provider_down` event in the Redis pub/sub channel.

---

### Phase 5 — Influencer Extraction & Identity Resolution (1 day)

**Goal**: each crawled page produces one canonical Influencer record
per real human being, with confidence and provenance. Identical
mentions across pages merge into the same canonical record.

**Current state**:

* `extract_influencer_mentions(page)` returns mention dicts with name,
  handle, platforms, credentials, contact info, authority mentions,
  context window, and a deterministic `mention_id`.
* `extract_influencers` Celery task persists each mention as an
  `Influencer` row (creating new rows when missing) and links each
  mention to its `CrawlSource` via the `CrawlSourceInfluencer` join.
* `canonicalize_candidate` / `merge_candidates` / `resolve_candidates`
  in `backend/pipeline/identity/` perform merge decisions.
* `resolve_identity_llm` task exists but only reconciles **two**
  candidates on demand; there is no campaign-wide cluster pass.

**Gaps**:

* No campaign-wide cluster pass that emits `identity.merged` events.
* `extract_influencers` always creates one `Influencer` row per
  mention (the row identity is the `canonicalize_candidate(mention)`
  output), so the identity resolution happens implicitly at extraction
  time — there is no second pass that catches later merges.
* The merge logic in `resolve_identity_clusters` is implemented but
  never invoked by a Celery task.

**Actions**:

1. **Wire `resolve_identity_clusters` into the pipeline**:
   * Add `backend/pipeline/tasks/extract.py::resolve_identity_cluster`
     that, after `extract_influencers` for a given `crawl_source_id`,
     loads all `Influencer` rows for the campaign and runs
     `resolve_identity_clusters(candidates, campaign_id=campaign_id,
       event_emitter=publish_event)`.
   * Emit `identity.merged` events (already supported by the resolver)
     and persist merge provenance to `Influencer.source_provenance`.
2. **Confidence threshold for auto-merge**: require
   `decision.confidence ≥ 0.85` for an automatic merge. Lower
   confidences route to `ambiguous_pairs` and emit
   `identity.ambiguous` events that the frontend can surface.
3. **Handle LLM fallback**: when `AI_AGENT_LLM_IDENTITY=1`, hand off
   the ambiguous pair to `resolve_identity_llm.delay(...)` (already
   exists) and let its verdict close the loop.
4. **Tests**:
   * `test_resolve_identity_clusters.py` — two near-duplicate mentions
     merge into one canonical record; a confidence < 0.85 pair is
     routed to ambiguous.
   * `test_resolve_identity_emits_events.py` — patch `publish_event`
     and confirm `identity.merged` events fire.
   * `test_low_confidence_routes_to_llm.py` — when flag is on, a low
     confidence pair schedules `resolve_identity_llm`.

**Verification**:

* `pytest backend/tests/pipeline/test_extraction.py test_identity.py
   test_celery_tasks.py -v` passes.
* New tests pass.
* Manual: run a real campaign, observe at most one row per real
  person in the `influencers` table.

---

### Phase 6 — Scoring & Fusion (1 day)

**Goal**: every Influencer row is scored deterministically with
sub-scores, confidence, grade, model version, and provenance. Optional
ML adapters layer in only when their flags are set, and they bump the
model version to v2 without breaking the v1 contract.

**Current state** (the orchestrator is mature):

* `run_role5_pipeline(candidate, campaign)` runs every stage:
  4 fake-risk scorers → detection classifier → 6 sub-scorers → 5-layer
  fusion → trust → score event.
* `fusion.components` calls `ml_adapters.semantic_v2_score` /
  `behavioral_v2_score` and reports v2 usage through
  `signal_model_versions`.
* `fusion.trust.calculate_role5_trust` applies the three documented
  caps.
* `events.ScoreCalculated.to_payload()` always redacts `contact_info`.

**Gaps**:

* `run_role5_pipeline` returns `Role5PipelineResult` (rename in Phase 1).
* No integration test that runs the full pipeline against the database
  with a real `Influencer` row. Today the test mocks the session.
* No documented "minimum evidence" rule. Today `confidence = Low` is
  hard-coded when `data_source_count < 3` but that should also degrade
  the cap on the final score (already done by `trust.py`'s "Sparse-data
  cap" — confirm with an explicit test).

**Actions**:

1. **Rename `Role5PipelineResult` → `Role4PipelineResult`** (alias
   retained in Phase 1).
2. **Add `run_role4_pipeline` to be the canonical entry point** that
   the Celery `score_influencer` task calls.
3. **Document the score-version bump**: `MODEL_VERSION_V2 = "Role4-InfluenceScore-v2"`
   triggered by any v2 adapter firing; document the rule in
   `docs/Role-4-Pipeline-Intelligence.md` under "Score Outputs".
4. **Add an integration test** `test_score_influencer_e2e.py` that:
   * Creates a real `Campaign`, two `CrawlSource` rows, and an
     `Influencer` row with two mentions (using SQLite-compatible types
     via the existing patching harness in `test_celery_tasks.py`).
   * Calls `score_influencer.delay(...)`.
   * Asserts the resulting `InfluencerScore` row has
     `final_score ∈ [0, 100]`, `score_version == MODEL_VERSION_ROLE4`,
     a non-empty `positive_reasons` / `negative_reasons`, and
     `signal_scores` keys.
5. **Sparse-data deterministic degradation**: extend
   `trust.calculate_role5_trust` (rename in Phase 1) with a
   `confidence_multiplier` for `data_source_count < 3` that scales
   the final score by `min(1.0, data_source_count / 3)`. Cover with
   a unit test that checks the multiplier activates.
6. **Stable reasoning order**: `analysis.reason_builder.build_reasons`
   must return reasons in deterministic order so events replay
   identically. Add a test that asserts `set(reasons_a) == set(reasons_b)`
   and `reasons_a == reasons_b`.

**Verification**:

* `pytest backend/tests/pipeline/test_orchestrator.py test_scoring.py
   test_role5.py test_renormalized_fusion.py -v` passes.
* New integration test passes.

---

### Phase 7 — Event Safety & Provenance (½ day)

**Goal**: every event that flows through Redis is replay-safe,
PII-redacted, and versioned. The frontend can rely on the documented
event taxonomy.

**Current state**:

* `backend/pipeline/events/__init__.py` defines `InfluencerFound`,
  `IdentityMerged`, `ScoreCalculated`.
* `ScoreCalculated.to_payload()` redacts `contact_info` through
  `redact_contact_info` (SHA-256 truncated).
* The Celery tasks publish raw dicts to `publish_event(...)`, not
  always going through the `events` module — see below.

**Gaps**:

* The Celery `score.py` task publishes a raw dict for `score.calculated`
  instead of using `events.ScoreCalculated`. The orchestrator builds a
  `score_event` for the orchestrator's own return value, but the
  Celery event bypasses that redaction. This is a real PII risk.
* The taxonomy of event types is implicit (event names appear as
  strings throughout the tasks). The Role-4 doc promises a documented
  taxonomy.

**Actions**:

1. **Refactor `score_influencer`** so the event payload it publishes is
   `result.score_event` (the orchestrator already builds it through
   `events.ScoreCalculated`). Drop the manual dict construction at the
   bottom of `score_influencer`.
2. **Refactor `search.py` / `crawl.py` / `extract.py`** so every
   `publish_event(...)` call goes through one of the dataclasses in
   `backend/pipeline/events/`. Add new dataclasses as needed:
   * `QueryGenerationCompleted`
   * `SearchExecuted`
   * `PageFetched`
   * `ContentExtracted`
   * `InfluencerFound` (already exists)
   * `InfluencersNone`
   * `IdentityResolved`
   * `IdentityMerged` (already exists)
   * `ScoreCalculated` (already exists)
   * `BrandSafetyFlagged`
   * `CampaignCancelled`
3. **Document the taxonomy** in `docs/Role-4-Pipeline-Intelligence.md`
   under "Events" — append a table of `event_type`, payload fields,
   and which task emits it.
4. **Add a redaction test** that injects raw contact info into the
   candidate, calls `run_role4_pipeline`, and asserts the emitted
   `score_event["contact_info"]` contains only SHA-256-truncated
   hashes while `result.contact_info` retains the plain text.

**Verification**:

* `rg "publish_event" backend/pipeline/tasks/` shows every call is
  inside an `events.<Dataclass>(...).to_payload()` call.
* `pytest backend/tests/pipeline/test_role5.py test_celery_tasks.py
   -v` passes.
* `pytest backend/tests/pipeline/test_contact_info.py -v` passes and
  the new redaction test is included.

---

### Phase 8 — ML Adapter Integration (1 day)

**Goal**: the optional `backend.ml` package plugs into the orchestrator
without changing its public contract. CI exercises the smoke path.

**Current state**:

* `backend/pipeline/fusion/backends/ml_adapters.py` already exports
  `semantic_v2_score`, `behavioral_v2_score`, `graph_v2_score`,
  `bot_rings_v2_score`, `explain_via_llm` behind env flags.
* `backend/ml/semantic_v2.py`, `backend/ml/behavioral.py`,
  `backend/ml/final_risk.py` etc. are stubs that return `None`.
* `backend/tests/pipeline/test_ml_smoke.py` and `test_ml_adapters.py`
  cover the wiring.

**Gaps**:

* The actual model implementations in `backend/ml/` are largely
  skeleton / placeholder. They compile but return `None`.
* The LLM explainer is not invoked from any Celery task.

**Actions**:

1. **Make `backend.ml.semantic_v2.SemanticEngineV2` real**:
   * Read pre-trained model checkpoints from
     `backend/ml/models/checkpoints/...` (use deterministic placeholder
     weights for now).
   * Implement `score(features) -> float | None` that returns 0-100
     for spam / toxicity / AIGC signals.
2. **Make `backend.ml.behavioral.BehavioralEngine` real** with the
   same pattern.
3. **Wire `explain_via_llm` into `score_influencer`** so the
   `score_event["explanation"]` field carries LLM-generated text when
   `ML_USE_LLM_EXPLAINER=1`.
4. **CI smoke job**: add a `ml-smoke` GitHub Actions job that
   * exports `ML_USE_SEMANTIC_V2=1 ML_USE_BEHAVIORAL_V2=1
     ML_USE_LLM_EXPLAINER=1`
   * runs `pytest backend/tests/pipeline/test_ml_smoke.py -v`
   * confirms the orchestrator now reports v2 model versions in the
     emitted events.
5. **Document the flag matrix** in `docs/Role-4-Pipeline-Intelligence.md`
   under "Key Workflows → Optional ML Adapters".

**Verification**:

* `pytest backend/tests/pipeline/test_ml_smoke.py -v` passes with all
  flags on.
* `pytest backend/tests/pipeline/test_ml_adapters.py -v` passes.
* Manual: enable `ML_USE_SEMANTIC_V2=1` in dev, observe
  `risk_score.model_version == "Role4-InfluenceScore-v2"`.

---

### Phase 9 — Documentation, Handoffs & Final Review (½ day)

**Goal**: the Role-4 charter is self-contained and a new engineer can
implement a change against it without spelunking.

**Actions**:

1. **Append the event taxonomy table** to
   `docs/Role-4-Pipeline-Intelligence.md`.
2. **Append the ML flag matrix** to the same file.
3. **Add a "Quickstart" section** that links to:
   * the orchestrator entry point
   * the queue topology
   * the test commands
   * the durable-contract assertions
4. **Cross-link** `docs/Role-3-Backend.md` and `docs/Role-2-Frontend.md`
   to the new event taxonomy and the renamed public surface.
5. **Final review checklist**:
   * Every "Owns" directory has at least one test file.
   * Every "Durable Contract" claim is covered by a test that fails if
     the contract is broken.
   * Every event type in the taxonomy is asserted at least once in
     `backend/tests/pipeline/test_celery_tasks.py` or
     `test_role4_scraping.py`.
   * `pytest backend/tests/ -v` is green on the default branch.

**Verification**:

* `pytest backend/tests/ -v` is green.
* `rg "TODO|FIXME|XXX" backend/pipeline/ backend/ml/` returns no
  hits for items owned by Role 4.
* A reviewer can read `docs/Role-4-Pipeline-Intelligence.md` plus this
  plan and onboard without asking any questions.

---

## 4. Risk Register

| Risk                                                  | Mitigation                                                                   |
| ----------------------------------------------------- | ---------------------------------------------------------------------------- |
| Rename breaks the API / frontend                      | Keep aliases for one release; only add new names; coordinate with Role 3.    |
| `extract_influencers` already merges duplicates       | The new cluster pass is **idempotent** (already-canonical pairs stay merged).|
| ML adapters blow up test runtime                      | ML tests are gated behind env vars and skipped by default.                   |
| Circuit breaker wedges a provider open forever         | 5-minute cool-down + manual `redis-cli del role4:provider_fail:...` escape.  |
| Contact info leak via Celery event                    | Phase 7 refactor forces every event through `events.*` dataclasses.         |

---

## 5. Test Strategy

| Layer                | Tooling                                | Coverage goal |
| -------------------- | -------------------------------------- | ------------- |
| Unit                 | `pytest backend/tests/pipeline/`       | 95% lines on `backend/pipeline/fusion/`, `analysis/`, `detection/`, `events/`, `identity/`. |
| Integration          | `test_celery_tasks.py`, `test_role4_scraping.py`, `test_role5.py` | End-to-end happy path + 3 failure paths. |
| Contract             | New `test_durable_contracts.py`        | Every claim under "Durable Contracts" in `Role-4-Pipeline-Intelligence.md` has a failing-then-passing assertion. |
| Smoke (ML)           | `test_ml_smoke.py`                     | All ML flags on → v2 model version emitted. |
| Manual / staging     | Real campaign run                      | One row per real person; no PII in event stream. |

---

## 6. Acceptance Criteria (Definition of Done)

The Role-4 charter is "implemented end to end" when **all** of the
following are true:

1. `pytest backend/tests/ -v` is green on the default branch.
2. Every Celery task in `backend/pipeline/tasks/` ships on the queue
   declared in `backend/core/celery/roles.py` (covered by
   `test_queue_routing.py`).
3. Every Celery task publishes its events through
   `backend/pipeline/events/` and the published payloads match the
   taxonomy documented in `Role-4-Pipeline-Intelligence.md`.
4. Every scored influencer has `source_url` or `source_urls`, sub-scores,
   `final_score`, `confidence`, `grade`, `score_version`, and a
   non-empty explanation (covered by
   `test_score_influencer_e2e.py`).
5. The contact-info contract holds: raw PII lives only on the
   `Influencer` ORM row; the public `score_event` always carries
   SHA-256-truncated values (covered by `test_contact_info.py`).
6. The orchestrator returns `Role4PipelineResult` (or its alias) and
   the score event carries `model_version == "Role4-InfluenceScore-v1"`
   for the all-heuristics path and `"Role4-InfluenceScore-v2"` when
   any ML adapter fires.
7. The ML flag matrix is documented and CI runs the smoke path.
8. The event taxonomy, the ML flag matrix, the quickstart, and the
   cross-links to Role 2 / Role 3 are present in
   `docs/Role-4-Pipeline-Intelligence.md`.

---

## 7. Sequencing & Effort

| Phase | Title                                  | Effort   | Dependencies |
| ----- | -------------------------------------- | -------- | ------------ |
| 1     | Alignment & renaming                   | 1 day    | —            |
| 2     | Queue topology & Celery wiring         | 0.5 day  | 1            |
| 3     | Query planning                         | 1 day    | 2            |
| 4     | Search / fetch / extraction            | 1 day    | 2            |
| 5     | Extraction & identity resolution       | 1 day    | 4            |
| 6     | Scoring & fusion                       | 1 day    | 5            |
| 7     | Event safety & provenance              | 0.5 day  | 6            |
| 8     | ML adapter integration                 | 1 day    | 6            |
| 9     | Documentation & final review           | 0.5 day  | 7, 8         |

**Total**: ~7.5 engineering days of focused work, plus review / QA buffer.
Phases 3-5 and 7-8 can run in parallel after Phase 2 lands, which compresses
calendar time to ~3-4 working days for two engineers.

---

## 8. Open Questions for the User

1. **Public surface rename**: do we keep `Role5*` symbols as aliases
   indefinitely, or do we remove them after one release? (Default plan:
   keep for one release, then delete.)
2. **ML smoke in CI**: is `pytest backend/tests/pipeline/test_ml_smoke.py`
   fast enough to run on every PR, or should it be nightly only?
   (Default plan: every PR — the smoke tests are mocked.)
3. **Provider circuit breaker**: 5 failures / 60 s / 5 min cool-down is
   the proposal. Confirm or adjust.
4. **Sparse-data confidence multiplier**: scale by `min(1.0, count/3)` is
   the proposal. Confirm or adjust.
