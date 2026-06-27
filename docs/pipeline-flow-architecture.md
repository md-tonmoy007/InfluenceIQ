# InfluenceIQ — AI Pipeline Architecture

This document captures the **execution flow** for influencer discovery and analysis: phases, Celery tasks, queues, and data movement through the pipeline.

It covers two product flows:

1. **Normal search** — discover and rank influencers for a campaign brief.
2. **Deep search** — perform comment-level AI analysis on a selected influencer and produce a report.

**How this doc relates to others**

| Document | Scope |
| --- | --- |
| **[architecture.md](./architecture.md)** | System source of truth — REST/WebSocket contracts, campaign lifecycle (create, submit, **rerun**, cancel), data models |
| **This doc** | What happens **once the pipeline is dispatched** — `generate_queries` through scoring and optional deep analysis |
| [development.md](./development.md) | Local setup and day-to-day dev workflow |

**Running a campaign** spans both layers: the API persists the brief and chooses *when* to start (or restart); this document describes *what runs* after `start_campaign` enqueues `generate_queries`.

---

## Overview

```mermaid
flowchart TB
    subgraph discovery["Phase 1 — Discovery & Search"]
        Campaign["Build a campaign"]
        QueryAgent["Query agent<br/><i>query generation</i>"]
        Cache1[("Cache")]
        SearchAPI["Search API"]
        Scraper["Scrape<br/><i>web crawl</i>"]
    end

    subgraph platforms["Platform enrichment"]
        YT["YouTube"]
        TT["TikTok"]
        IG["Instagram"]
    end

    subgraph scoring_phase["Phase 2 — Extraction & Scoring"]
        ExtractAgent["Extract agent"]
        Cache2[("Cache")]
        Weights["Campaign parameters<br/><i>scoring weights</i>"]
        Scoring["Scoring<br/><i>top-N list</i>"]
    end

    subgraph deep["Phase 3 — Deep analysis"]
        Influencer["Selected influencer"]
        Comments["Comment corpus<br/><i>~10k comments</i>"]
        PerPost["Per-post comments"]
        CommentAI["Comment analysis AI"]
        Report["Report"]
    end

    Campaign --> QueryAgent
    Cache1 -.-> QueryAgent
    QueryAgent -->|"each query"| SearchAPI
    SearchAPI -->|"webpage links"| Scraper

    Scraper --> YT
    Scraper --> TT
    Scraper --> IG
    Scraper -->|"engagement signals"| Scoring
    Scraper --> ExtractAgent
    Cache2 -.-> ExtractAgent
    ExtractAgent --> Scoring
    Weights --> Scoring

    Scoring --> Influencer
    Influencer -->|"comments, likes, recent views"| Comments
    YT --> Comments
    TT --> Comments
    IG --> Comments
    Comments --> PerPost
    PerPost --> CommentAI
    CommentAI --> Report
```

---

## Phase 1 — Discovery & Search

The discovery phase turns a brand brief into search queries, finds public web pages, and crawls them for creator signals.

```mermaid
sequenceDiagram
    actor Brand
    participant API as FastAPI
    participant QA as Query agent
    participant Cache as Redis cache
    participant Search as Search API
    participant Crawl as Scraper

    Brand->>API: POST /api/campaigns or POST /submit or POST /rerun
    Note over API: Rerun clears campaign run artifacts first (see below)
    API->>QA: start_campaign → generate_queries(campaign_id)
    QA->>Cache: read query / page cache
    QA-->>QA: plan queries<br/>e.g. "best influencer in Singapore for medical"
    loop each query
        QA->>Search: execute_search(campaign_id, query)
        Search-->>Crawl: webpage URLs
        Crawl->>Cache: cache fetched HTML / metadata
    end
```

### Components

| Component | Role | Example |
| --- | --- | --- |
| **Build a campaign** | Capture brand brief, target audience, platforms, region, and scoring weights | Medical brand in Singapore, YouTube + Instagram |
| **Pipeline dispatch** | Commit lifecycle state and enqueue the root task | `start_campaign` → `generate_queries.delay` |
| **Query agent** | Generate campaign-specific search queries from the brief | `"best medical influencer Singapore site:youtube.com"` |
| **Cache** | Avoid redundant LLM calls, search results, and page fetches | Redis URL cache (global), query dedup; campaign-scoped pipeline state |
| **Search API** | Execute web search and return candidate URLs | Brave, OpenSerp |
| **Scrape** | Fetch pages, extract readable content, discover social profile links | httpx fetch + content extraction (Firecrawl-style crawl in the target design) |

### Pipeline entry points

All normal-search runs converge on the same execution graph after dispatch:

| Trigger | API | When to use |
| --- | --- | --- |
| **Create + start** | `POST /api/campaigns` (`start_pipeline=true`) | New brief, run immediately |
| **Submit draft** | `POST /api/campaigns/{id}/submit` | Saved draft, first run |
| **Quick rerun** | `POST /api/campaigns/{id}/rerun?start_pipeline=true` | Terminal campaign (`completed`, `failed`, `cancelled`, `partial`); same brief, fresh pipeline on same `campaign_id` |
| **Edit & rerun** | `POST /api/campaigns/{id}/rerun?start_pipeline=false` then `PATCH` + `submit` | Change brief before the next run |

Rerun does **not** create a new campaign row. It clears the previous run's outputs and re-enters at **Query generation** (see [Rerunning a campaign](#rerunning-a-campaign)).

### Data flow

```mermaid
flowchart LR
    Brief["Campaign brief"] --> Params["Parameters<br/>industry · region · platforms · weights"]
    Params --> Queries["Search queries"]
    Queries --> URLs["Discovered URLs"]
    URLs --> Pages["Fetched pages + HTML"]
    Pages --> Links["Social profile links<br/>YouTube · TikTok · Instagram"]
```

---

## Phase 2 — Extraction & Scoring

Once pages are crawled, the system extracts influencer mentions, resolves identities, enriches platform engagement, and produces a weighted trust score.

```mermaid
flowchart TB
    Pages["Crawled pages"]

    subgraph extract["Extract agent"]
        Mentions["Influencer mentions<br/>names · handles · credentials"]
        Identity["Identity resolution<br/>canonical profiles"]
    end

    subgraph signals["Signal inputs"]
        Engagement["Engagement<br/>views · likes · comments"]
        Params["Campaign weights<br/>relevance · credibility · engagement · sentiment · safety"]
    end

    subgraph score["Scoring engine"]
        SubScores["Sub-scores"]
        Fusion["Weighted fusion"]
        TopN["Ranked top-N list"]
    end

    Pages --> Mentions
    Mentions --> Identity
    Identity --> SubScores
    Engagement --> SubScores
    Params --> Fusion
    SubScores --> Fusion
    Fusion --> TopN
```

### Scoring inputs

The scoring module combines three upstream paths shown in the diagram:

1. **Extract agent output** — names, handles, credentials, and source provenance from crawled content.
2. **Engagement data** — platform-specific metrics from YouTube, TikTok, and Instagram providers.
3. **Campaign parameters** — per-campaign weight overrides for relevance, credibility, engagement quality, sentiment, and brand safety.

```mermaid
flowchart LR
    subgraph inputs["Scoring inputs"]
        A["Extract agent"]
        B["Engagement from platforms"]
        C["Campaign weights"]
    end

    S["Scoring<br/>top 20 list"]
    A --> S
    B --> S
    C --> S
    S --> R["Ranked recommendations"]
```

### Platform providers

After scraping discovers social URLs, platform-specific fetchers enrich each candidate:

```mermaid
flowchart TB
    Scraper["Scraper / fetcher"]
    Scraper --> YT["YouTube provider<br/>channel · posts · comments"]
    Scraper --> TT["TikTok provider<br/>profile metadata"]
    Scraper --> IG["Instagram provider<br/>profile metadata"]

    YT --> Eng["Engagement signals"]
    TT --> Eng
    IG --> Eng
    Eng --> Scoring["Scoring"]
```

---

## Phase 3 — Deep Analysis

Deep analysis runs on one or more shortlisted influencers. It collects a large comment corpus (the diagram targets ~10,000 comments), analyzes engagement quality per post, and produces an AI-generated report.

```mermaid
flowchart TB
    Shortlist["Top influencer from scoring"]

    subgraph collect["Comment collection"]
        Posts["Recent posts"]
        Metrics["Views · likes · comment counts"]
        Corpus["Comment corpus<br/>up to ~10k comments"]
    end

    subgraph analyze["Comment analysis AI"]
        PerPost["Per-post comment analysis"]
        Sentiment["Sentiment & trust signals"]
        Fake["Fake / bot engagement detection"]
        Safety["Brand-safety screening"]
    end

    Report["Influencer report"]

    Shortlist --> Posts
    Posts --> Metrics
    Posts --> Corpus
    Corpus --> PerPost
    PerPost --> Sentiment
    PerPost --> Fake
    PerPost --> Safety
    Sentiment --> Report
    Fake --> Report
    Safety --> Report
```

### Deep analysis sequence

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI
    participant Deep as Deep analysis task
    participant YT as YouTube
    participant TT as TikTok
    participant IG as Instagram
    participant AI as Comment analysis AI

    User->>API: Select influencer for deep analysis
    API->>Deep: deep_analyze(influencer_id)

    par platform fetch
        Deep->>YT: recent posts + comments
        Deep->>TT: recent posts + comments
        Deep->>IG: recent posts + comments
    end

    Deep->>Deep: aggregate comment corpus (~10k)
    loop each post
        Deep->>AI: analyze comments, likes, views
        AI-->>Deep: sentiment, fake signals, safety flags
    end
    Deep-->>API: report payload
    API-->>User: influencer analysis report
```

### Report outputs

The comment analysis AI produces explainable outputs per influencer:

- Audience sentiment and trust indicators
- Fake or low-quality engagement risk
- Brand-safety concerns with cited evidence
- Per-post breakdowns (views, likes, comment quality)
- Overall recommendation grade with confidence

---

## End-to-end pipeline (both flows)

```mermaid
stateDiagram-v2
    [*] --> CampaignCreated: POST /api/campaigns
    CampaignCreated --> QueryGeneration: start_campaign → generate_queries
    QueryGeneration --> Searching: execute_search (per query)
    Searching --> Crawling: fetch_page (per URL)
    Crawling --> Extracting: extract_content → extract_influencers
    Extracting --> Enriching: enrich_influencer_platforms
    Enriching --> Scoring: score_influencer (per candidate)
    Scoring --> Ranked: top-N recommendations
    Ranked --> Terminal: completed / partial / failed / cancelled

    Terminal --> QueryGeneration: POST /rerun (reset artifacts, start_pipeline=true)
    Terminal --> DraftForEdit: POST /rerun (start_pipeline=false)
    DraftForEdit --> QueryGeneration: PATCH brief + POST /submit

    Ranked --> DeepAnalysis: user selects influencer
    DeepAnalysis --> ReportReady: comment analysis complete
    ReportReady --> [*]
```

Phase 1–2 (normal search) ends at **Terminal**. **Rerun** loops back to **QueryGeneration** on the same `campaign_id` after clearing run-scoped data. Phase 3 (deep analysis) remains user-triggered and is not started automatically by rerun.

---

## Rerunning a campaign

Rerun replays the **same execution graph** as a first run. The lifecycle layer (`POST /rerun` in [architecture.md](./architecture.md)) handles reset and dispatch; the pipeline layer is unchanged after `generate_queries` starts.

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI
    participant Reset as campaign_reset
    participant Redis as Redis
    participant Start as start_campaign
    participant QA as generate_queries

    User->>API: POST /api/campaigns/{id}/rerun
    API->>Reset: clear_campaign_run_artifacts (Postgres)
    Note over Reset: scores, crawl_sources, flags, snapshots, deep_analysis_runs
    API->>Redis: clear pipeline_state, pipeline_events, event_id_counter
    alt start_pipeline=true (quick rerun)
        API->>Start: _dispatch_pipeline → start_campaign
        Start->>QA: generate_queries.delay
    else start_pipeline=false (edit & rerun)
        API-->>User: status=draft (edit brief, then submit)
    end
```

### What rerun clears vs preserves

| Layer | Cleared on rerun | Preserved |
| --- | --- | --- |
| **Postgres (run artifacts)** | `crawl_sources`, `influencer_scores`, `brand_safety_flags`, `candidate_snapshots`, `deep_analysis_runs` | `campaigns` row (brief, weights), `campaign_contracts`, `saved_list_items`, global `influencers` |
| **Redis (campaign-scoped)** | `pipeline_state:{id}`, `pipeline_events:{id}`, `event_id_counter:{id}` | — |
| **Redis (global)** | — | URL/page cache (`url_cache:*`) — reruns may skip re-fetching unchanged pages |

Clearing run artifacts is required: `refresh_campaign_status` derives completion from Postgres. Re-dispatching without deleting old scores and extracted sources can mark the campaign **completed** before new work finishes.

Global URL cache is **intentionally kept** for faster reruns. If a bad run was caused by stale cached pages, operators may need cache eviction separately; that is not part of the default rerun path.

### Outreach guard

If the campaign has shortlisted or contracted creators, quick rerun (`start_pipeline=true`) returns `409 rerun_has_outreach` unless the client sends `X-Confirm-Rerun: true`. Contracts and saved-list items are kept; only match results are replaced.

---

## Worker queue mapping

The pipeline maps onto three Celery queues:

```mermaid
flowchart LR
    subgraph ai["ai_agent_queue"]
        GQ["generate_queries"]
        LLM["optional LLM decisions"]
    end

    subgraph scrape["scraping_queue"]
        ES["execute_search"]
        FP["fetch_page"]
        EC["extract_content"]
    end

    subgraph score_q["scoring_queue"]
        EI["extract_influencers"]
        RI["resolve_identity"]
        EN["enrich_influencer_platforms"]
        SI["score_influencer"]
    end

    GQ --> ES
    ES --> FP
    FP --> EC
    EC --> EI
    EI --> RI
    RI --> EN
    EN --> SI
```

| Diagram component | Celery task / module | Queue |
| --- | --- | --- |
| Query agent | `generate_queries` | `ai_agent_queue` |
| Search API | `execute_search` | `scraping_queue` |
| Scrape | `fetch_page`, `extract_content` | `scraping_queue` |
| Extract agent | `extract_influencers`, `resolve_identity_cluster` | `scoring_queue` |
| Platform enrichment | `enrich_influencer_platforms` | `scoring_queue` |
| Scoring | `score_influencer` | `scoring_queue` |
| Campaign rerun | `POST /rerun` → reset + `start_campaign` | API / orchestrator |
| Comment analysis AI | `deep_analyze` *(planned)* | TBD |

---

## Implementation status

| Phase | Component | Status |
| --- | --- | --- |
| 1 | Campaign intake | Implemented — `POST /api/campaigns` |
| 1 | Campaign rerun | Implemented — `POST /api/campaigns/{id}/rerun` (see [Rerunning a campaign](#rerunning-a-campaign)) |
| 1 | Query agent + cache | Implemented — deterministic queries + optional LLM; Redis cache |
| 1 | Search API | Implemented — Brave / OpenSerp with fallback |
| 1 | Scrape / crawl | Implemented — httpx fetch + content extraction |
| 2 | Extract agent | Implemented — spaCy/regex + optional LLM extraction |
| 2 | Platform providers | Partial — YouTube richest; TikTok/Instagram shallow |
| 2 | Weighted scoring | Implemented — fusion engine with campaign weights |
| 3 | Deep analysis (10k comments) | **Not yet implemented** — analyzers exist but are not wired to real comment data |
| 3 | Report generation | **Not yet implemented** |

See [Status-Report.md](./Status-Report.md) for a detailed gap analysis.

---
