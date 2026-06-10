# Backend Checklist

Current backend status by system capability.

## Status Legend

| Status | Meaning |
| --- | --- |
| Done | Implemented as working backend behavior. |
| Demo | Wired into the pipeline, but currently uses demo or deterministic placeholder behavior instead of real production behavior. |
| Not Done | Planned or documented, but not implemented in the current backend. |

## Top-Level Checklist

| Capability | Status | Current Behavior |
| --- | --- | --- |
| Campaign creation | Done | Backend accepts a campaign brief and creates a campaign record. |
| Pipeline startup | Done | Campaign creation starts the backend discovery pipeline. |
| Pipeline state tracking | Done | Backend stores campaign phase, status, counts, and errors in Redis. |
| Live event stream | Done | Backend emits pipeline events and streams them over WebSocket. |
| Event replay on reconnect | Done | WebSocket reconnect can replay previous campaign events using `last_event_id`. |
| Campaign state API | Done | Frontend can poll campaign status and pipeline state. |
| Influencer results API | Done | Frontend can fetch saved influencer recommendations for a campaign. |
| Filtering and sorting results | Done | Influencer results support platform, grade, follower filters, and sorting. |
| Health endpoint | Done | Backend reports DB, Redis, queue, and worker status. |
| Queue observability | Done | Backend exposes queue depth, worker, active task, reserved task, and failed result summaries. |
| Email/password authentication | Done | Backend supports signup, login, logout, and current-user lookup. Passwords are stored as hashes. |
| Cookie session authentication | Done | Backend issues an HttpOnly session cookie for authenticated browser requests. |
| Campaign owner isolation | Done | Campaign creation, campaign reads, influencer results, state reads, and campaign WebSockets require the owning user. |
| Search query creation | Done | Backend generates campaign-specific search queries through the configured LLM provider, with deterministic fallback only if the provider call fails. |
| Web search execution | Done | Backend executes real web discovery using SerpApi when configured, with Brave Search and a `scrape.do`-fetched search results page as fallbacks. |
| URL discovery | Done | URLs are discovered from live search results instead of generated `example.com` placeholders. |
| Page fetching | Done | Backend fetches live page HTML through `scrape.do`, with deterministic fallback only when the provider is unavailable. |
| Scraping | Done | Scraping flow fetches real websites through `scrape.do`, which handles much of the anti-bot and rendering overhead. |
| HTML cleanup | Done | Backend strips HTML from fetched page content before downstream extraction. |
| Social link discovery | Done | Backend extracts handles and social links from fetched page HTML content. |
| Influencer extraction | Demo | Backend extracts names, handles, and credentials using regex-style rules from demo content. |
| Credential detection | Demo | Backend detects simple credential terms like `MD`, `PhD`, `RD`, `RN`, and `Certified`. |
| Identity deduplication | Demo | Backend lightly deduplicates influencers by normalized name or handle. Full multi-source identity resolution is not implemented. |
| Brand safety check | Demo | Backend checks deterministic keyword risks. LLM classification is not implemented. |
| Trust scoring | Demo | Backend calculates sub-scores and a weighted final score using deterministic rules. |
| Score confidence | Done | Backend caps confidence and scores when there are too few data sources. |
| Score grades | Done | Backend assigns grades from the final score. |
| Result persistence | Done | Backend saves campaign influencer results in the database. |
| Partial results concept | Done | Campaign state indicates whether partial influencer results are available. |
| Celery worker routing | Done | Search, crawl, extract, and score workers are separated by queues. |
| PostgreSQL storage | Done | Campaigns and campaign influencer results are stored. |
| Redis storage | Done | Pipeline state, event logs, queue broker, and task results use Redis. |

## Not Done Checklist

| Capability | Status | Gap |
| --- | --- | --- |
| Real LLM query generation | Done | Query generation now calls the configured OpenRouter-compatible model and falls back deterministically only on provider failure. |
| Real search provider integration | Done | Search now uses SerpApi when configured, with Brave Search and a `scrape.do` search-page fallback when needed. |
| Real webpage crawling | Done | Backend now fetches live websites over HTTP through `scrape.do`. |
| URL cache before crawling | Done | Crawled pages are cached in Redis by URL hash before refetching. |
| Per-domain rate limiting | Done | Crawling now applies Redis-backed per-domain throttling, with a longer interval for supported social domains and cache hits bypassing the limiter. |
| Anti-ban scraping strategy | Done | Fetching now retries on timeouts, 403/429/5xx responses, and bot-block markers, then falls back to `web.archive.org` through `scrape.do` when retries are exhausted. |
| Recursive crawl depth | Done | Discovery now follows a depth-2 crawl policy from search result pages into supported profile and same-domain about/profile pages, with campaign-level URL dedupe and a 100-URL cap. |
| Real social platform scraping | Demo | Direct profile enrichment is implemented for YouTube and TikTok only. YouTube uses the official Data API, TikTok uses scraper-first HTML parsing, and other platforms remain unsupported. |
| Rich metadata extraction | Demo | Basic metadata extraction now captures common meta tags such as author, description, OpenGraph title, and published time, but source provenance tables are still not implemented. |
| spaCy or NLP entity extraction | Not Done | Current extraction is deterministic pattern matching only. |
| Full identity resolution | Not Done | URL hash matching, fuzzy matching, and LLM merge decisions are not fully wired into the pipeline. |
| Audience sentiment analysis | Not Done | Backend does not collect or analyze real audience comments. |
| Fake engagement detection | Not Done | Spam ratio, generic comment ratio, and engagement mismatch detection are not implemented against real social data. |
| Real follower and engagement metrics | Not Done | Followers and engagement are not collected from real platforms. |
| LLM brand-safety classification | Not Done | Backend only performs keyword checks. |
| Source-level audit records | Not Done | Dedicated `crawl_sources` and `brand_safety_flags` tables from the architecture are not implemented. |
| Score history | Not Done | Scores are saved as current campaign results, not as append-only historical scoring records. |
| pgvector semantic matching | Not Done | Embedding-based matching is documented but not implemented. |
| Company workspace sharing | Not Done | Users do not yet share campaigns inside a company workspace. Campaigns are scoped to the creating user only. |
| API key authentication | Not Done | Machine-to-machine API keys and key-based rate limits are not implemented. |
| Email verification and password reset | Not Done | Signup does not verify email addresses, and password reset email flow is not implemented. |
| Export reports | Not Done | No backend report export endpoint is implemented. |
| Demo reset endpoint | Not Done | No `/api/demo/reset` endpoint is implemented. |

## Current Backend Pipeline

1. Brand submits campaign details.
2. Backend creates a campaign and marks it as queued.
3. Backend starts the pipeline in the background.
4. Backend generates search queries from the campaign brief through the configured LLM provider.
5. Backend executes live web search and collects result URLs.
6. Backend checks the Redis URL cache, applies per-domain throttling, retries blocked fetches, and uses archive fallback when live fetches fail repeatedly.
7. Backend performs a depth-2 recursive crawl, following supported YouTube and TikTok profile links plus same-domain about/profile pages.
8. Backend extracts cleaned content, metadata, discovered links, and platform profile URLs from fetched HTML.
9. Backend enriches YouTube creators through the official YouTube Data API and enriches TikTok creators from scraped profile payloads.
10. Backend checks brand-safety keywords and merges article/about citations into the best normalized creator identity.
11. Backend calculates scores and grades.
12. Backend stores campaign influencer results.
13. Backend marks the campaign completed or failed.
14. Frontend can read results through REST APIs or live WebSocket events.

## Practical Summary

The backend has the workflow shell done: campaign intake, pipeline orchestration, worker queues, state tracking, WebSocket updates, scoring output, result storage, and result APIs.

The backend now has live query generation, recursive crawling, YouTube API enrichment, and TikTok scraper enrichment in place, but it still lacks broader platform coverage, advanced NLP extraction, deeper identity resolution, audience analysis, and LLM-based safety/scoring analysis.

Parts of discovery and platform enrichment are now live for YouTube and TikTok, but much of extraction, trust analysis, and wider social intelligence remain demo-level.
