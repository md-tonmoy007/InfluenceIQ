# InfluenceIQ — AI Pipeline Architecture

This document captures the end-to-end influencer discovery and analysis pipeline as designed in the product architecture diagram. It covers two product flows:

1. **Normal search** — discover and rank influencers for a campaign brief.
2. **Deep search** — perform comment-level AI analysis on a selected influencer and produce a report.

For runtime topology, API contracts, and data models, see [architecture.md](./architecture.md).

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

    Brand->>API: POST /api/campaigns (brief, weights, platforms)
    API->>QA: generate_queries(campaign_id)
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
| **Query agent** | Generate campaign-specific search queries from the brief | `"best medical influencer Singapore site:youtube.com"` |
| **Cache** | Avoid redundant LLM calls, search results, and page fetches | Redis URL cache, query dedup |
| **Search API** | Execute web search and return candidate URLs | Brave, OpenSerp |
| **Scrape** | Fetch pages, extract readable content, discover social profile links | httpx fetch + content extraction (Firecrawl-style crawl in the target design) |

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
    CampaignCreated --> QueryGeneration: generate_queries
    QueryGeneration --> Searching: execute_search (per query)
    Searching --> Crawling: fetch_page (per URL)
    Crawling --> Extracting: extract_content → extract_influencers
    Extracting --> Scoring: score_influencer (per candidate)
    Scoring --> Ranked: top-N recommendations
    Ranked --> DeepAnalysis: user selects influencer
    DeepAnalysis --> ReportReady: comment analysis complete
    ReportReady --> [*]
```

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
        SI["score_influencer"]
    end

    GQ --> ES
    ES --> FP
    FP --> EC
    EC --> EI
    EI --> RI
    RI --> SI
```

| Diagram component | Celery task / module | Queue |
| --- | --- | --- |
| Query agent | `generate_queries` | `ai_agent_queue` |
| Search API | `execute_search` | `scraping_queue` |
| Scrape | `fetch_page`, `extract_content` | `scraping_queue` |
| Extract agent | `extract_influencers`, `resolve_identity_cluster` | `scoring_queue` |
| Scoring | `score_influencer` | `scoring_queue` |
| Comment analysis AI | `deep_analyze` *(planned)* | TBD |

---

## Implementation status

| Phase | Component | Status |
| --- | --- | --- |
| 1 | Campaign intake | Implemented — `POST /api/campaigns` |
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
