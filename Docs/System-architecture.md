# Problem Statement

Brands today spend enormous amounts of time and money trying to find the right influencers for marketing campaigns. Most existing influencer discovery platforms focus mainly on vanity metrics such as follower count, likes, or impressions. However, these metrics alone are not enough to determine whether an influencer is actually trustworthy, credible, or aligned with a brand's reputation.

A major problem in influencer marketing is the lack of trust-aware discovery systems. Brands often struggle with issues such as:

- Fake followers and fake engagement
- Influencers promoting unrelated or misleading products
- Lack of professional credibility in sensitive niches like healthcare, finance, or fitness
- Poor audience trust and negative sentiment
- Controversial or unsafe content that can damage brand reputation
- Difficulty discovering niche experts across platforms
- Manual research taking hours or days

For example, a healthcare brand may accidentally collaborate with a fitness creator who has large reach but no actual medical or nutritional expertise. Similarly, a financial brand may partner with creators who spread misinformation or have low audience trust.

Current systems do not deeply analyze:

- Whether the influencer is actually qualified to speak on a topic
- Whether audiences genuinely trust the creator
- Whether engagement is organic or manipulated
- Whether the influencer presents brand safety risks

As influencer marketing grows, brands increasingly need a system that does not just discover influencers, but evaluates how trustworthy and credible they are.

The goal of this project is to build an AI-powered trust-aware influencer discovery platform that helps brands discover influencers and rank them based on credibility, audience trust, engagement quality, and brand safety.

The system should:

- Automatically discover influencers from the web
- Analyze their public content and audience engagement
- Detect credibility indicators and risk factors
- Generate explainable trust scores
- Recommend the best influencers for a specific campaign

Instead of simply answering:

> "Who is popular?"

The platform answers:

> "Who should a brand actually trust?"

---

# Whole Architecture Plan

# 1. High-Level System Flow

```text
Brand Inputs Campaign Information
            ↓
AI Generates Search Queries
            ↓
[search_queue] → Celery Workers Execute Web Search
            ↓
Search APIs Discover Relevant Pages
            ↓
[crawl_queue] → Celery Workers: Recursive Scraping & Content Extraction
            ↓             (with URL cache check → skip if recently visited)
[extract_queue] → Celery Workers: Influencer Entity Extraction
            ↓
Identity Resolution & Deduplication
            ↓
Social Handle Discovery
            ↓
[score_queue] → Celery Workers: Trust & Credibility Analysis
            ↓
Audience Sentiment Analysis
            ↓
Brand Safety Detection
            ↓
Trust Scoring Engine (normalized sub-scores → weighted formula)
            ↓
Ranked Influencer Recommendations
            ↓
Pipeline State stored in Redis → WebSocket event replay on reconnect
            ↓
Dashboard & Real-Time Visualization
```

---

# 2. Architecture Philosophy

The system is designed as a:

- Fast-shipping modular monolith
- Real-time streaming pipeline
- AI-assisted hybrid analysis system
- Fault-tolerant async task system (Celery + Redis)

Instead of building a distributed microservice infrastructure, the project will prioritize:

- Faster development
- Easier debugging
- Simpler deployment
- Better hackathon execution

The architecture follows a modular monolith approach where all components exist inside a single backend system while remaining logically separated. Async processing is handled via Celery with Redis as the message broker, giving fault tolerance and task observability without microservice complexity.

---

# 3. Frontend Architecture

## Technology Stack

- Next.js
- TailwindCSS
- React
- WebSockets
- shadcn/ui

## Responsibilities

The frontend acts as the main interface for brands to:

- Submit campaign details
- View live workflow progress (with reconnection-safe event replay)
- Explore influencer recommendations
- Understand trust score explanations
- Review brand safety warnings

---

## Frontend Modules

### A. Campaign Submission Interface

Brands provide:

- Product information
- Industry/niche
- Campaign goals
- Target audience
- Preferred platforms
- Budget range

Example:

```text
Product: Vegan Protein Powder
Industry: Fitness
Target Audience: Gym Enthusiasts
Platform Preference: Instagram & YouTube
```

---

### B. Real-Time Workflow Visualization

The frontend streams live pipeline updates from the backend via WebSocket.

Example:

```text
✓ Generating search queries
✓ Searching the web
✓ Scraping influencer pages  [23/47 URLs processed]
✓ Extracting creator profiles
✓ Calculating trust scores
```

All pipeline events are stored in Redis (TTL: 1 hour) keyed by campaign ID. On WebSocket reconnect, the backend replays all past events so the frontend reconstructs its state correctly without data loss.

---

### C. Influencer Recommendation Dashboard

Displays:

- Influencer ranking
- Trust grades
- Engagement quality
- Audience sentiment
- Credibility indicators
- Brand safety flags
- Platform links
- Score freshness indicator (when score was last computed)

---

### D. Trust Score Explanation Panel

One of the most important features of the system.

Example:

```text
Trust Grade: A+

Reasons:
+ Verified fitness coach
+ High positive audience sentiment
+ Mentioned in authority health blogs
+ Strong engagement quality
- Moderate sponsorship saturation

Score confidence: High (sufficient data collected)
Score version: v1.2 | Last computed: 2 hours ago
```

This creates explainability and transparency.

---

# 4. Backend Architecture

## Technology Stack

- FastAPI
- Python
- Celery (async task processing)
- Redis (message broker + pipeline state cache + URL cache)
- PostgreSQL + pgvector

The backend acts as:

- Workflow orchestrator
- AI coordinator
- Scraping manager
- Scoring engine
- Real-time event streamer

---

# 5. API Layer

The backend exposes:

- REST APIs
- WebSocket streams

## REST APIs

Used for:

- Campaign creation
- Influencer retrieval
- Dashboard data
- Exporting reports
- Pipeline state polling (fallback if WebSocket is unavailable)

---

## WebSocket Layer

Used for:

- Real-time scraping updates
- Pipeline progress
- Live trust score updates

### Reconnection Handling

All pipeline events are appended to a Redis list keyed by `pipeline_events:{campaign_id}` (TTL: 1 hour). On WebSocket reconnect, the server replays the full event list to restore frontend state. This prevents data loss on mobile or flaky connections.

---

# 6. AI Query Generation System

## Purpose

Convert brand campaign information into intelligent search queries.

The system uses LLMs only where reasoning is required.

---

## Input Example

```json
{
  "product": "Protein Shake",
  "industry": "Fitness",
  "target_audience": "Gym Users"
}
```

---

## Generated Queries

```text
top fitness influencers instagram
trusted gym creators youtube
nutrition experts on instagram
best fitness product reviewers
```

---

## AI Model Usage

LLMs are used for:

- Query generation
- Semantic understanding
- Score explanation
- Brand safety content classification
- Identity resolution edge cases (low-confidence deduplication)

Deterministic systems are used for:

- Extraction
- Crawling
- Pattern matching
- First-pass keyword filtering (brand safety blocklist before LLM)

This hybrid architecture reduces cost and improves speed.

---

# 7. Search Layer

## Purpose

Discover relevant web pages containing influencer references.

---

## APIs Used

- OpenSerp
- Brave Search API

---

## Search Targets

- Blog articles
- YouTube profiles
- Instagram pages
- Review websites
- Creator rankings
- Authority articles

---

## Output

The search layer returns:

- URLs
- Titles
- Snippets
- Relevance scores

---

# 8. Recursive Crawling Engine

## Purpose

Visit discovered pages and extract influencer-related information.

---

## Crawl Depth Strategy

Maximum crawl depth:

```text
Depth = 2
```

Flow:

```text
Search Result
    ↓
Article
    ↓
Referenced Social Profile
```

This prevents:

- crawler explosion
- excessive runtime
- duplicate data
- noisy extraction

---

## URL-Level Caching

Before fetching any URL, the crawler checks a Redis cache keyed by `url_cache:{url_hash}` (TTL: 48 hours).

```text
URL received
    ↓
Check Redis url_cache
    ├── Cache HIT → return cached content, skip fetch
    └── Cache MISS → fetch page → store in Redis → continue pipeline
```

This eliminates redundant scraping of the same pages across campaigns and dramatically improves demo speed when the same influencers appear in multiple search results.

---

## Rate Limiting & Anti-Ban Strategy

Social platforms aggressively block scrapers. The crawler implements:

- Per-domain request throttling stored in Redis (1 request per 2 seconds for social platforms)
- Rotating user-agent headers
- Playwright headless fingerprint randomization
- Exponential backoff on 429 and 403 responses (initial delay: 2s, max: 60s)
- Fallback to web-archived versions of pages when blocked

Per-domain throttle state is stored in Redis as `rate_limit:{domain}` with a sliding window counter.

---

## Technologies

- Playwright (JavaScript-rendered pages, fingerprint randomization)
- BeautifulSoup (static HTML parsing)
- HTTPX (async HTTP requests)

---

## Responsibilities

The crawler:

- checks URL cache before fetching
- fetches page HTML with rate limit enforcement
- extracts readable content
- discovers social profile links
- collects metadata
- streams crawl progress via WebSocket

---

# 9. Content Extraction System

## Purpose

Extract clean text and metadata from webpages.

---

## Extracted Data

- Article title
- Main content
- Author names
- Social links
- Mentioned creators
- Embedded profiles

---

## Processing Pipeline

```text
Raw HTML
    ↓
HTML Cleaning
    ↓
Content Extraction
    ↓
Metadata Extraction
    ↓
Source URL recorded (for score provenance)
```

Source provenance (which URL each data point came from) is recorded at this stage and propagated through to the final trust score. This enables the Trust Score Explanation Panel to cite sources.

---

# 10. Influencer Entity Extraction Engine

## Purpose

Identify influencers mentioned in content.

---

## Responsibilities

Extract:

- influencer names
- Instagram handles
- YouTube channels
- profile URLs
- creator descriptions
- credentials

---

## Methods Used

### Deterministic Extraction

- Regex
- URL parsing
- Pattern matching

### NLP-Based Extraction

- spaCy
- LLM extraction for edge cases

---

## Example Output

```json
{
  "name": "Dr Sarah Tan",
  "instagram": "@drsarahtan",
  "youtube": "youtube.com/sarahtan",
  "source_url": "https://healthblog.example.com/top-nutritionists"
}
```

---

# 11. Identity Resolution Layer

## Purpose

Merge duplicate influencer identities discovered across multiple pages and platforms.

---

## Problem

The same influencer may appear across sources as:

```text
Dr Sarah Tan
Sarah Tan MD
@sarahtanfit
youtube.com/sarahtan
```

---

## Resolution Strategy (Three-Pass)

Resolution runs in three passes, cheapest first:

**Pass 1 — Profile URL Hash Match**
Exact match on normalized social profile URLs. Zero-cost, handles most duplicates.

**Pass 2 — Fuzzy Name + Username Similarity**
Levenshtein distance on display names and username stems. Merges when confidence >= 0.85.

**Pass 3 — LLM Resolution**
For low-confidence cases (0.6–0.84 similarity), a lightweight LLM prompt decides merge or keep-separate. Used sparingly to control cost.

**Data Model**

Each resolved influencer stores:

```json
{
  "influencer_id": "canonical-uuid",
  "canonical_name": "Dr Sarah Tan",
  "mentions": [
    { "name": "Sarah Tan MD", "source": "healthblog.example.com" },
    { "name": "@sarahtanfit", "source": "instagram.com" }
  ],
  "platforms": {
    "instagram": "@drsarahtan",
    "youtube": "youtube.com/sarahtan"
  }
}
```

---

# 12. Social Intelligence Layer

## Purpose

Analyze influencer quality and audience trust.

---

## Data Collected

### Engagement Metrics

- likes
- comments
- views
- posting frequency

### Audience Metrics

- follower counts
- engagement ratios
- audience interaction quality

### Sentiment Signals

- positive comments
- spam comments
- toxicity indicators

---

# 13. Fake Engagement Detection

## Purpose

Detect suspicious engagement behavior.

---

## MVP Approach

A lightweight heuristic-based system.

---

## Signals Used

### Generic Comment Detection

Example:

```text
Nice 🔥🔥🔥
Amazing ❤️
```

---

### Engagement Mismatch

Flags:

- huge follower counts
- extremely low engagement

---

### Spam Ratio

High repetitive comments increase suspicion score.

---

## Example Calculation

```text
Bot Probability =
  (spam_ratio * 0.4) +
  (engagement_mismatch * 0.4) +
  (generic_comment_ratio * 0.2)

All inputs normalized to [0, 1] before weighting.
```

---

# 14. Credibility Analysis Engine

## Purpose

Determine whether the influencer is qualified to discuss the topic.

This is the core differentiator of the platform.

---

## Example

A fitness creator discussing:

- medical advice
- nutrition
- supplements

should ideally have:

- certifications
- educational credentials
- authority mentions

---

## MVP Scoring Rules

| Signal                          | Score |
| ------------------------------- | ----- |
| Verified account                | +10   |
| Professional title              | +15   |
| Mentioned in authority websites | +20   |
| Educational credentials         | +20   |
| Positive sentiment              | +15   |
| High engagement quality         | +10   |
| Spam indicators                 | -20   |
| Brand safety risks              | -25   |

Raw score is normalized to [0, 100] before being passed to the Trust Scoring Engine.

---

# 15. Brand Safety Detection

## Purpose

Warn brands about risky influencers.

The system does not automatically reject influencers. It only flags potential concerns.

---

## Detection Method (Two-Pass)

**Pass 1 — Keyword Blocklist**
Fast pre-filter against a curated blocklist of high-risk terms. Runs before any LLM call to reduce cost.

**Pass 2 — LLM Classification**
Extracted content is sent to an LLM with the prompt:

```text
Does this content contain any of the following risks?
- hate speech
- medical misinformation
- financial scams
- political extremism
- excessive undisclosed sponsorships
- toxic engagement patterns

Answer: yes/no for each. If yes, provide a one-sentence reason.
```

Results are stored with the source URL for auditability.

---

## Detected Risks

- controversial content
- hate speech
- misinformation
- scams
- toxic engagement
- political extremism
- excessive sponsorship behavior

---

## Example Warning

```text
⚠ Brand Safety Warning:
Influencer promoted controversial medical claims.
Source: instagram.com/drsarahtan (post from 2024-11)
```

---

# 16. Trust Scoring Engine

## Purpose

Generate final influencer trust ratings that are normalized, weighted, and versioned.

---

## Inputs

All sub-scores are individually normalized to [0, 100] before entering the formula.

### Relevance Score

How aligned the influencer is with the niche.

### Credibility Score

Professional authority and expertise.

### Engagement Quality

Audience interaction authenticity (inverse of Bot Probability).

### Sentiment Score

Audience trust level.

### Brand Safety Score

Risk assessment (100 = no risk, 0 = high risk).

---

## Normalization

Each sub-score must be on the [0, 100] scale before weighting. Low-data influencers receive a confidence penalty: if fewer than 3 data sources contributed to a sub-score, that sub-score is capped at 70 to prevent misleadingly extreme values.

---

## Weight System

Brands can customize weights via the campaign submission interface.

Default weights:

```text
Final Score =
  0.30 * Relevance +
  0.30 * Credibility +
  0.20 * Engagement +
  0.10 * Sentiment +
  0.10 * Brand Safety
```

---

## Score Versioning

Every score record stores:

- `score_version` — formula version that produced this score
- `computed_at` — timestamp
- `data_source_count` — number of sources used
- `confidence_level` — High / Medium / Low

This allows scores to be re-computed when the formula updates without losing historical data, and surfaces freshness to the user on the dashboard.

---

## Score History

Scores are never overwritten. Each scoring run appends a new record linked to the influencer and campaign. This enables trend tracking in Phase 2.

---

## Final Grades

| Score  | Grade |
| ------ | ----- |
| 90–100 | A+    |
| 80–89  | A     |
| 70–79  | B     |
| 60–69  | C     |
| <60    | D     |

---

# 17. Recommendation Engine

## Purpose

Return the best influencers for the campaign.

---

## Features

### Ranking

Sort influencers by:

- trust
- relevance
- authority
- engagement quality

---

### Filtering

Brands can filter by:

- platform
- niche
- region
- follower size
- trust grade

---

# 18. Real-Time Streaming System

## Purpose

Provide transparency into the AI workflow and survive connection interruptions.

---

## Architecture

```text
Celery Worker emits event
        ↓
Event appended to Redis List  [pipeline_events:{campaign_id}]  TTL: 1 hour
        ↓
FastAPI WebSocket handler reads new events and pushes to client
        ↓
Frontend Live Updates

On reconnect:
        ↓
Client sends campaign_id on reconnect handshake
        ↓
Server replays full Redis event list to restore frontend state
```

---

## Example Events

```text
query.generated        { queries: [...] }
url.discovered         { url, title, relevance }
url.cache_hit          { url }
page.scraped           { url, status }
page.rate_limited      { url, retry_in }
influencer.found       { name, platform, source }
identity.merged        { canonical_id, merged_from }
score.calculated       { influencer_id, grade, confidence }
pipeline.completed     { total_influencers, duration_seconds }
```

---

# 19. Database Architecture

## PostgreSQL Schema (Key Tables)

### campaigns

Stores brand campaign submissions.

### influencers

Stores canonical influencer records with `influencer_id`, `canonical_name`, `platforms` (JSONB), `mentions` (JSONB array).

### influencer_scores

Stores one record per scoring run. Never overwritten.

| Column             | Type      | Notes                        |
| ------------------ | --------- | ---------------------------- |
| score_id           | UUID      | Primary key                  |
| influencer_id      | UUID      | Foreign key → influencers    |
| campaign_id        | UUID      | Foreign key → campaigns      |
| final_score        | FLOAT     | Weighted final score [0–100] |
| relevance_score    | FLOAT     | Normalized sub-score         |
| credibility_score  | FLOAT     | Normalized sub-score         |
| engagement_score   | FLOAT     | Normalized sub-score         |
| sentiment_score    | FLOAT     | Normalized sub-score         |
| brand_safety_score | FLOAT     | Normalized sub-score         |
| confidence_level   | TEXT      | High / Medium / Low          |
| data_source_count  | INT       | Sources used in scoring      |
| score_version      | TEXT      | Formula version              |
| computed_at        | TIMESTAMP |                              |

### crawl_sources

Stores per-URL extraction records. Each row links a data point back to its source URL for provenance and explainability.

### brand_safety_flags

Stores per-influencer flags with source URL, risk type, and LLM-generated reason.

---

## Redis Key Design

| Key Pattern                     | Type   | TTL | Purpose                                  |
| ------------------------------- | ------ | --- | ---------------------------------------- |
| `url_cache:{url_sha256}`        | String | 48h | Cached page content, skip re-scrape      |
| `pipeline_events:{campaign_id}` | List   | 1h  | WebSocket event log for reconnect replay |
| `pipeline_state:{campaign_id}`  | Hash   | 2h  | Phase, counts, progress for polling      |
| `rate_limit:{domain}`           | String | 10s | Sliding window request counter           |
| `celery_task:{task_id}`         | String | 6h  | Celery task metadata                     |

---

## pgvector

Stores embeddings for:

- semantic influencer-to-campaign similarity
- influencer content embeddings for matching
- future recommendation systems

---

# 20. Async Processing: Celery + Redis

## Purpose

Handle all long-running scraping, extraction, and analysis tasks asynchronously with retry support, task chaining, and independent worker scaling per task type.

---

## Architecture

```text
FastAPI receives campaign request
        ↓
FastAPI dispatches root Celery task → returns campaign_id immediately to client
        ↓
┌─────────────────────────────────────────────────────────┐
│                     Redis Broker                        │
│                                                         │
│  search_queue   crawl_queue  extract_queue  score_queue │
└─────────────────────────────────────────────────────────┘
        ↓               ↓              ↓             ↓
  Search Workers  Crawl Workers  Extract Workers  Score Workers
  (2 workers)     (8 workers)    (4 workers)      (2 workers)
        ↓               ↓              ↓             ↓
                    PostgreSQL + Redis State
                            ↓
                  WebSocket event broadcast
```

Crawl workers are highest concurrency because the work is I/O-bound (network fetches). Extract workers are fewer because spaCy and LLM calls are CPU/token-bound. Search and score workers are low concurrency as their throughput is limited by external API rate limits.

---

## Queue Definitions

| Queue         | Worker Count | Task Types                                       |
| ------------- | ------------ | ------------------------------------------------ |
| search_queue  | 2            | AI query generation, Brave/OpenSerp API calls    |
| crawl_queue   | 8            | URL cache check, Playwright fetch, rate limiting |
| extract_queue | 4            | HTML cleaning, spaCy NLP, LLM entity extraction  |
| score_queue   | 2            | Trust scoring, brand safety LLM classification   |

---

## Task Chaining

Tasks are chained using Celery's `chain()` and `chord()` primitives:

```python
pipeline = chain(
    generate_queries.s(campaign_id),
    group(crawl_url.s(url) for url in discovered_urls),
    chord(
        group(extract_influencers.s(page) for page in crawled_pages),
        score_all_influencers.s(campaign_id)
    )
)
pipeline.apply_async()
```

---

## Retry Policy

All tasks use exponential backoff:

```python
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=2,
    autoretry_for=(RequestException, PlaywrightTimeoutError),
    retry_backoff=True,
    retry_backoff_max=60,
)
```

Failed tasks after max retries are logged to PostgreSQL and their URLs marked as `status: failed` in the pipeline state, allowing partial results to still be returned.

---

## Pipeline State & Partial Results

Campaign pipeline state is stored in Redis as a hash:

```json
{
  "campaign_id": "abc123",
  "phase": "crawling",
  "urls_discovered": 47,
  "urls_scraped": 23,
  "urls_failed": 4,
  "influencers_found": 11,
  "scores_computed": 6
}
```

If the pipeline fails mid-run, the system returns all influencers scored so far rather than an empty result. The frontend displays a banner indicating partial results.

---

## Celery Worker Configuration

```python
celery_app = Celery(
    "influenceiq",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
)

celery_app.conf.task_routes = {
    "tasks.search.*":  {"queue": "search_queue"},
    "tasks.crawl.*":   {"queue": "crawl_queue"},
    "tasks.extract.*": {"queue": "extract_queue"},
    "tasks.score.*":   {"queue": "score_queue"},
}

celery_app.conf.task_serializer = "json"
celery_app.conf.result_expires = 21600  # 6 hours
```

---

# 21. Observability & Health Dashboard

## Purpose

Provide real-time visibility into worker health, queue depths, and failure rates — critical for debugging during live demos and production operation.

---

## Tools

- **Flower** — Celery monitoring UI. Displays per-worker task throughput, queue depths, failed tasks, and retry counts. Accessible at `/flower` in development.
- **Redis INFO** — queue depth monitoring via `LLEN` on each queue key.
- **FastAPI health endpoint** — `GET /health` returns queue depths, worker counts, and DB connection status.

---

## Health Endpoint Response

```json
{
  "status": "ok",
  "queues": {
    "search_queue": 0,
    "crawl_queue": 12,
    "extract_queue": 5,
    "score_queue": 2
  },
  "workers": {
    "crawl": 8,
    "extract": 4,
    "search": 2,
    "score": 2
  },
  "db": "connected",
  "redis": "connected"
}
```

---

## Key Metrics to Monitor

| Metric             | Alert Threshold | Action                            |
| ------------------ | --------------- | --------------------------------- |
| crawl_queue depth  | > 100 tasks     | Scale up crawl workers            |
| Task failure rate  | > 10%           | Check rate limit / IP ban status  |
| score_queue depth  | > 50 tasks      | Scale up score workers            |
| Redis memory usage | > 80%           | Increase TTLs, flush stale caches |

---

# 22. Deployment Architecture

## Hosting

- Railway or Render (FastAPI + Celery workers)
- Vercel (Next.js frontend)
- Redis Cloud or Railway Redis add-on
- PostgreSQL via Railway or Render managed database

---

## Container Strategy

Each Celery worker type runs as a separate process (or container in production):

```bash
# Search workers
celery -A app.celery worker -Q search_queue -c 2

# Crawl workers (highest concurrency)
celery -A app.celery worker -Q crawl_queue -c 8

# Extract workers
celery -A app.celery worker -Q extract_queue -c 4

# Score workers
celery -A app.celery worker -Q score_queue -c 2
```

---

## Why

The architecture prioritizes:

- rapid deployment
- simplicity
- low operational overhead
- fault tolerance without distributed systems complexity

---

# 23. Future Architecture Expansion

## Phase 2

Verification System:

- deeper credibility analysis with credential verification APIs
- advanced fraud detection using ML classifiers
- stronger identity matching via knowledge graph embeddings
- score trend tracking and influencer history

---

## Phase 3

Knowledge Graph:

- influencer relationship mapping
- trust networks and authority graphs
- cross-campaign influencer performance tracking
- recommendation engine powered by graph embeddings

---

# 24. Final System Summary

The platform is an AI-powered trust-aware influencer discovery system designed to help brands identify creators who are not only popular, but also credible, trustworthy, and safe for partnerships.

The system combines:

- AI query generation
- web search
- recursive scraping with URL caching and rate-limit protection
- NLP extraction with three-pass identity resolution
- brand safety detection via LLM classification
- normalized and versioned trust scoring
- Celery + Redis async task pipeline with retry and partial result support
- reconnection-safe WebSocket event streaming
- real-time observability via Flower and health endpoints

to produce explainable influencer recommendations.

Instead of optimizing for raw popularity, the platform optimizes for:

- trust
- credibility
- authenticity
- audience confidence
- brand alignment

This transforms influencer discovery from a manual and risky process into an intelligent, fault-tolerant, explainable, and scalable AI-driven workflow.
