---
title: "InfluenceIQ: A Trust-Aware AI Platform for Influencer Discovery"
subtitle: "SciBlitz AI Challenge 2026 — Project Report"
author:
  - "Team sudo_make_it_work"
  - "Rajshahi University of Engineering & Technology (RUET)"
date: "July 8, 2026"
geometry: margin=2.2cm
fontsize: 11pt
---

**Team:** sudo_make_it_work · **Institution:** RUET · **Track:** D — Open Innovation

**Team Lead:** MD Tonmoy Hossain Jifat (tonmoyhossainjifat313@gmail.com, 01987476056)

**Members:** MD Tonmoy Hossain Jifat, Shafayetul Huda Sadi, Adib Hasan, Mahmudul Hasan

**Live demo:** https://cuet.shafayetsadi.dev/ · **Repository:** https://github.com/md-tonmoy007/InfluenceIQ

---

## 1. Problem Statement

Influencer selection is still dominated by vanity metrics: follower counts, likes, and headline reach. Those numbers are easy to compare, but they do not answer the business question that matters: **which creator is actually trustworthy for this campaign?**

In practice, brands face three recurring problems:

1. **Inflated engagement.** Fake followers, spam comments, bot-like behavior, and coordinated engagement clusters can make a creator look more influential than they really are.
2. **Weak auditability.** Even when a team makes a good pick, the decision is often based on screenshots, intuition, and scattered tabs rather than stored evidence that can be reviewed later.
3. **Slow campaign research.** Manually checking creators across search results, articles, Instagram, TikTok, and YouTube is time-consuming and inconsistent from one reviewer to another.

The result is wasted spend, reputational risk, and a workflow that does not scale once a team needs to evaluate many candidates quickly.

## 2. Proposed Solution

**InfluenceIQ** is a trust-aware influencer discovery platform that turns a campaign brief into a ranked shortlist of creators, with source-backed scoring and live execution feedback.

A user can:

1. sign in and create a campaign brief,
2. launch the matching pipeline,
3. watch live progress as the system searches, crawls, extracts, enriches, and scores candidates,
4. review the ranked shortlist, creator profiles, saved lists, and outreach state, and
5. trigger a deeper per-creator analysis report when a shortlist candidate needs closer inspection.

Instead of returning only popularity metrics, the system combines campaign relevance, credibility, engagement quality, sentiment, brand safety, and source confidence into an explainable trust score. Every result is tied back to persisted sources and scoring records so the output remains auditable after the pipeline completes.

## 3. Methodology

### 3.1 Current system architecture

InfluenceIQ is implemented as a modular monolith with:

- a `Next.js` frontend for the product UI,
- a `FastAPI` backend for APIs and orchestration,
- `PostgreSQL` as the durable data store,
- `Redis` for Celery brokering, pipeline state, and event replay,
- three Celery worker roles for asynchronous campaign execution, and
- optional model/vector services for enhanced ML-backed behavior.

At product level, the current workspace includes:

- landing, signup, login, and onboarding,
- dashboard and workspace summary,
- campaign briefs and draft submission,
- discover and shortlist flows,
- saved lists,
- creator profile pages,
- deep-analysis report pages,
- account settings, integrations, API keys, and billing surfaces.

### 3.2 Pipeline flow

The main pipeline starts when the backend dispatches `start_campaign(campaign_id)`. The current execution graph is:

```text
start_campaign
  -> generate_queries
  -> execute_search
  -> fetch_page
  -> extract_content
  -> extract_influencers
  -> enrich_influencer_platforms
  -> score_influencer
  -> optional classify_brand_safety
```

This flow is distributed across three queues:

- `ai_agent_queue` for query planning, selected LLM-assisted tasks, and deep analysis
- `scraping_queue` for search, page fetch, extraction, and provider I/O
- `scoring_queue` for influencer extraction, identity clustering, and scoring

The pipeline is observable in real time through:

- a Redis-backed pipeline-state hash for polling, and
- a replayable WebSocket event stream keyed by `event_id`

This allows the frontend to reconnect and resume progress display without restarting the run.

### 3.3 Data model and evidence tracking

The current codebase persists the pipeline into explicit product tables rather than transient in-memory payloads. The most important entities are:

- `Campaign` for the brief, lifecycle status, and campaign context
- `CrawlSource` for discovered and fetched URLs
- `Influencer` for canonical creator identity
- `CrawlSourceInfluencer` for durable source-to-creator attribution
- `InfluencerScore` for versioned campaign-specific scoring outputs
- `BrandSafetyFlag` and `CredentialVerification` for risk and authority evidence
- `PlatformProfile`, `PlatformPost`, and `PlatformComment` for structured platform enrichment
- `DeepAnalysisRun` and `DeepAnalysisReport` for on-demand deeper review

This structure is central to the product claim: InfluenceIQ does not simply output a score, it stores the evidence path that led to that score.

### 3.4 Discovery and provider strategy

Discovery and enrichment use a provider stack with deterministic fallbacks:

- Brave Search is the primary search provider
- SerpAPI is a fallback search provider
- Instagram, TikTok, and X can use Apify-backed collection when tokens are configured
- YouTube uses its own public-page/RSS provider path, with optional upgrade paths documented in the repo
- Generic article fetching can use scrape.do or direct HTTP fetch

This design keeps the system usable in low-cost or partially configured environments while still improving quality when external provider credentials are available.

### 3.5 Deterministic-first AI/ML design

A core design choice in the current repository is **deterministic-first, ML-optional** behavior.

The product includes optional model-backed adapters for:

- spam/low-quality text classification,
- toxicity detection,
- AI-generated-text likelihood,
- LLM-based query planning and explanation,
- embedding-backed relevance,
- optional graph/model backends in `backend/ml`

However, the main scoring pipeline is designed to degrade gracefully when those adapters are unavailable. If a model backend cannot load or an external API is missing, the system falls back to deterministic heuristics rather than failing the campaign.

This is important for two reasons:

1. it keeps the live product operational in constrained environments, and
2. it makes the platform more auditable, because the baseline path is understandable and reproducible even without heavyweight model infrastructure.

### 3.6 Trust score formulation

The final trust score is implemented as a `0–100` score with grade bands:

- `A+` for `90–100`
- `A` for `80–89`
- `B` for `70–79`
- `C` for `60–69`
- `D` for `40–59`
- `F` for `0–39`

The current positive-score weights are:

| Sub-score          | Weight |
| ------------------ | ------ |
| Relevance          | 0.20   |
| Credibility        | 0.20   |
| Engagement quality | 0.15   |
| Sentiment          | 0.15   |
| Brand safety       | 0.15   |
| Source confidence  | 0.15   |

The pipeline then subtracts a fake-risk penalty:

`trust = positive_score - 0.5 × fake_risk`

The implementation also applies explicit caps so the system does not overstate trust when evidence quality is weak:

- overall fake-risk above `80` caps trust at `45`
- severe brand-safety risk caps trust at `40`
- fewer than `3` sources caps trust at `70`
- sparse evidence also applies a confidence multiplier based on source count

This means a creator cannot receive a high score purely from thin or suspicious evidence.

### 3.7 Deep analysis workflow

In addition to the main shortlist pipeline, the current product supports on-demand deep analysis for one creator within one campaign.

That workflow:

1. collects structured platform data already stored for the creator,
2. pulls recent posts and comment samples,
3. gathers additional external signals,
4. synthesizes a report, and
5. re-enqueues a creator rescore so richer evidence can flow back into the main trust view.

The current deep-analysis task is staged internally and emits its own progress events such as:

- `deep_analysis.started`
- `deep_analysis.social_collected`
- `deep_analysis.comments_collected`
- `deep_analysis.external_signals_collected`
- `deep_analysis.report_ready`

This gives the product a second layer of analysis beyond initial ranking: shortlist first, then investigate more deeply when needed.

## 4. Current Implementation Results

Based on the current repository state, InfluenceIQ now delivers the following implemented capabilities:

- A working full-stack product with authenticated workspace flows, campaign submission, dashboard views, shortlist views, creator profiles, and report pages.
- A real asynchronous campaign pipeline with queue separation, persisted lifecycle state, and WebSocket replay support.
- Canonical influencer records tied to durable crawl-source provenance.
- Versioned per-campaign scoring rows rather than one mutable score field.
- Saved lists and contract/outreach tracking that preserve user workflow after ranking.
- On-demand deep analysis with persisted reports and report retrieval endpoints.
- Optional ML-enhanced behavior without making the main product dependent on those models to function.

From a software-engineering perspective, the strongest result is not one single model or heuristic. It is the fact that the repo now represents a coherent product system: UI, API, async orchestration, evidence persistence, ranking, and re-analysis all exist inside one runnable architecture.

## 5. Limitations

The current codebase is functional, but several limitations remain clear.

### 5.1 Provider-dependent data depth

Search and platform quality depend on external provider availability. The system degrades gracefully, but the depth of Instagram/TikTok/X enrichment is significantly better when Apify-backed collection is configured than when only fallback scraping paths are available.

### 5.2 User-scoped product model

Most of the current workspace is user-scoped. Some data structures already contain placeholders such as `org_id`, but the implemented product model is not yet a full organization/team tenancy system with richer shared permissions.

### 5.3 Redis replay/state is operational, not archival

Pipeline events and fast state are stored in Redis with TTL-backed replay windows. PostgreSQL remains the durable source of truth, but the live replay layer is intentionally transient rather than a permanent historical event store.

### 5.4 Optional model stack is uneven

The repository includes optional ML and graph backends, but not every advanced path is equally mature. Some adapters are scaffolds or upgrade paths rather than the default execution path of the live product. The deterministic pipeline remains the authoritative baseline.

### 5.5 Human review is still limited

The platform persists evidence and flags, but it does not yet implement a full operator-facing human-review workflow for credential verification, brand-safety adjudication, or score override governance.

### 5.6 Deep analysis is targeted, not bulk

Deep analysis is currently an on-demand workflow for one `(campaign, influencer)` pair at a time. That is appropriate for shortlist investigation, but it is not yet a bulk second-pass pipeline for every ranked creator.

## 6. Future Work

The most valuable next steps suggested by the current codebase are:

1. Improve provider-backed data depth and consistency across platforms, especially when public fallbacks are shallow.
2. Expand from current user-scoped ownership to a fuller organization/team collaboration model.
3. Add stronger human-review tooling around flags, credentials, and final recommendations.
4. Mature optional ML-backed paths so more of them can move from experimental/upgrade status into routine production use.
5. Extend deep analysis from targeted report generation into richer campaign-level comparative workflows.
6. Improve long-term observability and analytics around completed pipeline runs, not only live execution state.

## 7. Conclusion

InfluenceIQ addresses a real gap in influencer selection: brands need a system that judges creators on trustworthiness and evidence quality, not only audience size.

The current repository now embodies that idea in a concrete product architecture. It accepts campaign briefs, runs an asynchronous search-to-score pipeline, persists evidence and scoring outputs, streams progress to the UI, and supports deeper creator investigation when a shortlist decision requires more confidence.

The project is not “finished” in a production sense, but it is no longer just a concept or slide-deck architecture. It is a working trust-aware influencer discovery system with clear extension points, auditable data flow, and a realistic path toward more advanced ML-assisted decision support.

## 8. Team & Contributions

| Member                              | Institution | Role                                                              |
| ----------------------------------- | ----------- | ----------------------------------------------------------------- |
| MD Tonmoy Hossain Jifat (Team Lead) | RUET        | Pipeline intelligence, scoring logic, trust/risk design           |
| Shafayetul Huda Sadi                | RUET        | Backend platform, orchestration, frontend integration, deployment |
| Adib Hasan                          | RUET        | Frontend implementation                                           |
| Mahmudul Hasan                      | RUET        | Scraping and scoring implementation                               |

---

_Repository: https://github.com/md-tonmoy007/InfluenceIQ · Live demo: https://cuet.shafayetsadi.dev/_
