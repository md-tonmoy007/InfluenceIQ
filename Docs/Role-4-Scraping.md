# Role 4: Scraping & Crawling Engineer

**Architecture Sections Owned:** 7 (search layer), 8 (crawling engine), 9 (content extraction)

You own the data engine. This is the highest-risk component because scraping breaks unpredictably. Start testing against real social platforms on Day 2 — not Day 5.

---

## Responsibilities

- Brave Search API + OpenSerp integration
- Playwright + BeautifulSoup page fetcher
- URL cache layer (Redis check before fetch, store after)
- Per-domain rate limiting (Redis sliding window)
- Exponential backoff on 429/403 responses
- Content extraction: HTML cleaning, readable text, social link discovery
- Source provenance tagging on every extracted data point
- Playwright fingerprint randomization (anti-ban)

---

## 7-Day Todo List

### Day 1 — Setup + Search

- [ ] Set up Brave Search API client (get API key, test query)
- [ ] Set up OpenSerp client as fallback
- [ ] Write `execute_search` Celery task in `search_queue`
- [ ] Output schema: list of `{url, title, snippet, relevance_score}`
- [ ] Get Celery task signatures from AI/DevOps lead
- [ ] Get Redis key schema for URL cache + rate limiting

### Day 2 — Basic Crawler + REAL TARGET TEST

- [ ] Set up Playwright with headless Chromium
- [ ] Write `fetch_page` Celery task in `crawl_queue`
- [ ] **CRITICAL:** Test against real Instagram profile, YouTube channel, Medium article on Day 2
- [ ] Document which platforms block immediately vs require workarounds
- [ ] Add HTTPX fallback for static HTML pages (faster than Playwright)
- [ ] Add randomized user-agent rotation

### Day 3 — URL Cache + Rate Limiting

- [ ] Implement URL cache check: before fetch, check `url_cache:{sha256(url)}`
  - Cache HIT → return stored content, skip fetch, emit `url.cache_hit` event
  - Cache MISS → fetch, store, continue
- [ ] Implement per-domain rate limiter using Redis sliding window
  - Key: `rate_limit:{domain}`, max 1 request per 2 seconds for social platforms
  - If rate limited → delay task with exponential backoff
- [ ] Emit `page.rate_limited` event when throttled

### Day 4 — Anti-Ban Hardening

- [ ] Playwright fingerprint randomization (viewport size, locale, timezone)
- [ ] Exponential backoff: 2s → 4s → 8s → 16s → 32s → max 60s
- [ ] Max retries: 3, after that mark URL as `status: failed`
- [ ] Add archived page fallback: if all retries fail, try `web.archive.org/web/{url}`
- [ ] Add proxy rotation hook (optional, only if blocks are severe)

### Day 5 — Content Extraction

- [ ] HTML cleaning: strip scripts, styles, ads, navigation
- [ ] Use `trafilatura` or `readability-lxml` for main content extraction
- [ ] Extract metadata: title, author, publish date, OpenGraph tags
- [ ] Discover and return all social profile links (Instagram, YouTube, TikTok, Twitter)
- [ ] Tag every extracted data point with source URL for provenance
- [ ] Write extracted records to `crawl_sources` PostgreSQL table

### Day 6 — Recursive Crawl + Integration

- [ ] Implement depth-2 recursive crawl: search result → article → linked social profile
- [ ] Hard cap on URLs per campaign (e.g., max 100) to prevent runaway
- [ ] Pass extracted profiles to `extract_queue` for entity extraction (Role 5)
- [ ] End-to-end test: search → crawl → cache → extract → DB write
- [ ] Verify partial results: if 4/10 URLs fail, the 6 successes still flow through

### Day 7 — Demo Prep

- [ ] Pre-warm URL cache with demo campaign URLs (so demo is fast)
- [ ] Verify rate limiter doesn't trigger on demo workload
- [ ] Have fallback: if live scraping is blocked during demo, return cached pages
- [ ] Document known platform limitations for judges
- [ ] Help debug any pipeline issues

---

## Key Files You Own

```
platform/
├── tasks/
│   ├── search.py             (execute_search task)
│   └── crawl.py              (fetch_page, extract_content tasks)
├── crawling/
│   ├── playwright_client.py
│   ├── httpx_client.py
│   ├── url_cache.py          (Redis read/write)
│   ├── rate_limiter.py       (Redis sliding window)
│   ├── fingerprint.py        (anti-ban randomization)
│   └── archive_fallback.py
├── extraction/
│   ├── html_cleaner.py
│   ├── content_extractor.py
│   ├── metadata.py
│   └── social_links.py
└── search/
    ├── brave_client.py
    └── openserp_client.py
```

## Implemented Role-5 Handoff Contract

Role 4 must pass each extracted page to Role 5 with a `role5_candidate`
payload. This keeps extraction/scoring deterministic and avoids forcing
Role 5 to infer scraper-specific fields.

```json
{
  "url": "https://source.example/article",
  "title": "Top Nutrition Creators",
  "content": "Clean readable text from the page",
  "social_links": ["https://instagram.com/drsarahtan"],
  "comments": ["Helpful and authentic advice"],
  "metrics": {
    "followers": 124000,
    "average_engagement": 5400,
    "verified": true
  },
  "metadata": {
    "description": "Evidence-based creator profile",
    "status": 200,
    "cached": false,
    "fetched_at": "2026-06-10T00:00:00+00:00",
    "fetch_provider": "httpx"
  },
  "provenance": {
    "source_url": "https://source.example/article",
    "status": 200,
    "cached": false
  },
  "role5_candidate": {
    "source_url": "https://source.example/article",
    "source_urls": ["https://source.example/article"],
    "bio": "Evidence-based creator profile",
    "content": "Clean readable text from the page",
    "context": "First 4000 chars for extraction/scoring",
    "comments": ["Helpful and authentic advice"],
    "followers": 124000,
    "average_engagement": 5400,
    "verified": true,
    "profile_urls": ["https://instagram.com/drsarahtan"],
    "data_source_count": 1,
    "source_evidence": {
      "data_source_count": 1,
      "profile_url_available": true,
      "metadata_completeness": 0.33
    }
  }
}
```

The campaign pipeline then merges `role5_candidate` with each extracted
mention from Role 5 extraction:

- `canonical_name`, `handle`, `platforms`
- `credentials`, `professional_titles`, `authority_mentions`
- `mentions`
- `source_urls`, `data_source_count`
- `brand_safety_scan`

This merged object is sent to `app.tasks.score.score_influencer`, which
can run the full Role 5 scoring path instead of the legacy five-number
shortcut.

## Platform Provider Adapters

Profile URLs now route through provider-specific adapters before the
generic HTTP fetcher:

- YouTube: public channel page metadata plus RSS feed posts when a channel
  ID is discoverable.
- Instagram: public `web_profile_info` endpoint using the public app ID,
  with profile meta fallback when the endpoint is blocked.
- TikTok: public profile metadata extraction from profile HTML.
- X/Twitter: public profile metadata extraction from profile HTML, with
  Twitter URLs normalized to `x.com`.

Every adapter returns a synthetic HTML page built from structured profile
data so the existing Role 4 extractor can produce the same
`role5_candidate` contract for all platforms.

The adapters intentionally degrade instead of failing hard. If a platform
blocks scraping, Role 4 still returns URL-derived identity and provenance
so Role 5 can mark the result as low-confidence rather than losing the
candidate entirely.

---

## Daily Dependencies

| Day | What You Need From Whom |
|-----|-------------------------|
| 1 | Celery task signatures (AI/DevOps), Redis key schema (AI/DevOps) |
| 2 | API keys for Brave + OpenSerp (AI/DevOps) |
| 5 | `crawl_sources` table schema (Backend), DB session for writes (Backend) |
| 6 | Extract task signature to chain into (Scoring) |

---

## Anti-Ban Playbook (Reference)

| Platform | Likely Behavior | Strategy |
|----------|-----------------|----------|
| Instagram | Blocks immediately without login | Use mobile user-agent, fetch public meta only, fallback to web.archive.org |
| YouTube | Allows public profile pages | Standard Playwright works, throttle to 1/3s |
| TikTok | Aggressive bot detection | Use web.archive.org fallback primarily |
| Medium / Substack | Open | HTTPX is enough, no Playwright needed |
| LinkedIn | Requires login | Skip in MVP, mark as future work |
| Personal blogs | Open | HTTPX + readability-lxml |

---

## Phase 2 — Verification System Crawling

- LinkedIn integration via official API (requires app approval)
- Certification site scrapers (e.g., NASM, CrossFit affiliates for fitness creators)
- Academic database lookup (Google Scholar, ResearchGate) for credibility signals
- Deeper crawl depth (3+) with smarter relevance filtering
- Headless browser farm with rotating residential proxies

## Phase 3 — Knowledge Graph Crawling

- Citation graph extraction: who mentions whom across articles
- Cross-platform identity linking via embedded social media links
- Build influencer co-occurrence dataset (which creators appear together in articles)
- Continuous crawling: scheduled re-crawls to track changes over time
- Webhook listeners for new content from priority influencers
