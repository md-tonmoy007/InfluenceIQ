# InfluenceIQ — Implementation Status Report

_Snapshot date: 2026-06-22. Scope: full-repo review against the two target product flows (Normal search, Deep search). No code was changed to produce this report._

## TL;DR

- **Normal search** is ~80% built and wired end-to-end: campaign → query → search → crawl → extract → identity → score → persist → WebSocket.
- **Deep search does not exist** — no endpoint, no task, no flow. This is the single biggest gap.
- The scoring/detection **engine is over-built** (5 detectors, 5-layer fusion, optional ML zoo) but is **starved of real per-influencer content** (views/comments/likes). The live scoring path passes empty comments.
- **Frontend and backend disagree on response shapes** — the UI cannot render live results without a contract fix.
- Tests: **260 passed, 2 failed, 9 skipped**; 3 ML test modules fail at import (optional deps missing). The Docker stack is **not currently running**.

---

## 1. Normal Search — mostly done

Full Celery fan-out chain exists and is correctly wired:

```
generate_queries
  -> execute_search          (per query)
       -> fetch_page         (per URL)
            -> extract_content
                 -> extract_influencers
                      -> resolve_identity_cluster
                      -> score_influencer   (per new influencer)
```

| Stage | Status | Notes |
| --- | --- | --- |
| Campaign intake (`POST /api/campaigns`) | Done | Idempotency-Key + DB unique-key dedup, optional auth, dispatches pipeline post-commit |
| Query generation | Done | Deterministic `_build_query_set` + dedup + platform coverage; optional LLM path behind `AI_AGENT_LLM_QUERY_PLANNING` with clean fallback |
| Web search | Done | Brave + OpenSerp providers, synthetic fallback when no API keys are set |
| Crawl / fetch | Done | httpx + per-platform providers, URL cache, circuit breaker, rate limiter, retries |
| Social providers | Partial | YouTube is richest (channelId + RSS feed -> posts/comments). TikTok / Instagram / X are meta-tag scrapers only, fragile, no real engagement/comment depth |
| Influencer extraction | Done | spaCy/regex entities, handles, credentials, contact info |
| Identity resolution | Done | fuzzy + URL match, auto-merge >= 0.85, ambiguous -> optional LLM |
| Scoring + persistence | Done | Full role-5 pipeline, append-only `InfluencerScore`, provenance links, brand-safety flags |
| State + events | Done | Redis `pipeline_state` + `pipeline_events` replay, WebSocket with `last_event_id` |

### Gaps vs. the intended Normal-search spec

- **Geolocation filtering: not implemented.** The spec calls for "filtering with geolocation and other metrics." There is no geo logic anywhere in the pipeline. Search is keyword-only; no region/country filter on queries or results.
- **TikTok / Instagram are shallow.** Only YouTube actually pulls posts + comments. TikTok/IG providers grab `og:description` and a follower regex and will mostly hit the fallback path on real sites (both platforms block server-side scraping aggressively).
- **Relevance scoring is thin.** `relevance_score` is token overlap between brief and influencer text — acceptable for MVP, but it is the heaviest-weighted component of the trust formula.

---

## 2. Deep Search — does not exist

Nothing in the repo implements the Deep search flow (pick an influencer, fetch recent content, analyze views/likes/comments to judge quality).

- No `/api/influencers/{id}/deep` (or equivalent) endpoint.
- No `deep_*` Celery task.
- No flow that re-fetches a chosen influencer's recent content and analyzes engagement.

**The analysis building blocks already exist but are never fed real data:**

- `analysis/sentiment.py`, `analysis/fake_comment.py`, and `detection/fake_comment_detector.py` all accept a `comments` list.
- `tasks/score.py::_build_candidate` **hardcodes `"comments": []`**. In the live pipeline, comment sentiment and fake-comment detection always run on empty input.

So Deep search is largely a **wiring + new-task job**: given a stored influencer, call the platform providers to pull recent posts/comments/engagement, then run the existing analyzers on real content instead of `[]`. The scoring brain exists; the data pipe into it does not.

---

## 3. Scoring / ML — over-built relative to need

- `pipeline/fusion` + `pipeline/detection` + `pipeline/analysis`: a full deterministic engine — 5 fake-risk detectors, 5-layer fusion with renormalization, trust formula, versioning, confidence caps, reason builder. Solid and well-tested.
- `backend/ml/` is a large optional model zoo (BERT-MoE, DeBERTa/DistilBERT spam, RoBERTa AIGC, toxic-bert, GAT/GCN/GraphSAGE, llama explainer, Qdrant/Mongo/MinIO stores). It is adapter-gated and **not installed** in the baseline env — `test_engines` / `test_adapters` / `test_bot_rings` fail at import (`networkx` missing). Consistent with the "deterministic baseline, ML optional" architecture, but a large surface area that is currently dead weight unless wired and its dependencies installed.

---

## 4. Frontend — built, but contract drift with backend

The Next.js app is substantial (landing, login/signup, briefs, discover, shortlist, profile, dashboard, settings, WebSocket client in `lib/websocket.ts`). However `lib/api.ts` and the backend disagree on response shapes:

- `getCampaignInfluencers` expects `{items, total, limit, offset, filters, sort}` with items shaped `{id, name, handle, platform, followers, engagementRate, matchScore, trustGrade, ...}`.
- Backend `GET /api/campaigns/{id}/influencers` returns `{items, next_cursor, limit}` with items shaped `{influencer_id, canonical_name, platforms, final_score, sub_scores{relevance, ...}, ...}`.
- `getCampaign` expects flat `{brand, product, category, goal, influencer_count, ...}`; backend returns `{campaign: CampaignResponse, pipeline_state}`.

Result: the discover/profile views will largely render undefined against live data. This is a real integration task before any live-data demo works.

---

## 5. Test / build health

- `260 passed, 2 failed, 9 skipped` (skips are Redis/SQLAlchemy not present in the bare test env).
- Failing:
  - `tests/api/test_backend_contracts.py::test_create_campaign_initializes_state_and_starts_pipeline`
  - `tests/pipeline/test_score_e2e.py::test_run_role4_pipeline_returns_Role4PipelineResult`
  - Likely env/contract-edge rather than core-logic failures; both deserve a direct look.
- 3 ML test modules error at collection (`networkx` not installed): `test_adapters.py`, `test_bot_rings.py`, `test_engines.py`.
- **Docker stack not running.** All `influenceiq-*` containers show `Exited (255) 2 weeks ago`. Host port mappings are non-standard: postgres `5434`, redis `6380`, qdrant `6335`, backend `8002`, flower `5555`, frontend `3002`.

---

## 6. What needs to be done (priority order)

1. **Build Deep search** — the headline missing feature. New endpoint + task that pulls a chosen influencer's recent content and runs the existing sentiment/engagement/fake-comment analyzers on real comments (stop passing `[]`).
2. **Fix frontend <-> backend response contracts** — otherwise the UI cannot show live results.
3. **Add geolocation filtering** to Normal search (queries + result filtering).
4. **Harden TikTok / Instagram providers**, or explicitly accept YouTube-first for the demo.
5. **Bring the Docker stack up** and run the 2 failing integration tests against real Redis/Postgres.
6. **Decide ML scope** — wire a couple of adapters in, or cut the dead `backend/ml/` weight for the hackathon.
