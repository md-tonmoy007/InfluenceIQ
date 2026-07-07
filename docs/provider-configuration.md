# Search and platform provider configuration

How InfluenceIQ chooses external services for **web search** (discovery) and **profile fetch** (per-platform scraping). All keys live in `backend/.env` (copy from `backend/.env.example`).

See also **Plan 06** sections below for the optional YouTube Data API and semantic-relevance embeddings knobs that upgrade data quality when keys are present.

## Two pipeline stages

| Stage | Job | Config namespace | Code |
| --- | --- | --- | --- |
| **Search** | Find candidate URLs from the campaign brief | `SEARCH_PROVIDER_MODE`, `BRAVE_*` | `backend/pipeline/content/search_providers.py` |
| **Fetch** | Pull profile data from a known URL | `APIFY_*`, `SCRAPE_DO_API` | `backend/pipeline/content/providers/`, `fetcher.py` |

Search and fetch are independent. Brave is **not** a YouTube scraper — it only helps discover URLs.

## Search providers

### Failover (default)

`SEARCH_PROVIDER_MODE=auto` picks a **single** provider per query (first success wins), then falls back to synthetic discovery URLs if all fail.

| `APP_ENV` | Primary | Fallback chain |
| --- | --- | --- |
| Any | Brave | → SerpAPI |

Override with explicit modes:

| Mode | Order |
| --- | --- |
| `brave` | Brave → SerpAPI |
| `serpapi` | SerpAPI → Brave |
| `all` | Call every configured provider and merge results (legacy behavior) |

### Brave Search API

```env
BRAVE_SEARCH_API_KEY=BSA...
```

Recommended for **judges / production** deploys. New accounts typically receive monthly credits (~1,000 searches); signup may require a card.

### SerpAPI (optional)

```env
SERP_API_KEY=...
```

Paid Google-shaped results; fallback in `auto` mode.

## Platform fetch providers

When `fetch_url()` sees a social profile URL, it routes to a platform-specific provider instead of generic HTTP fetch.

| Platform | Best path | Fallback chain | Apify actor default |
| --- | --- | --- | --- |
| **YouTube** | HTML + public RSS feed | synthetic fixture | — (no Apify) |
| **Instagram** | Apify | → Instagram web API → meta tags → URL-only | `apify/instagram-profile-scraper` |
| **TikTok** | Apify | → meta tags → URL-only | `clockworks/tiktok-profile-scraper` |
| **X / Twitter** | Apify | → meta tags → URL-only | `apify/twitter-scraper` |
| **Blogs / articles** | scrape.do (if set) | → httpx → synthetic fixture | — |

### Apify (Instagram, TikTok, X)

```env
APIFY_API_TOKEN=apify_api_...
APIFY_INSTAGRAM_ACTOR=apify/instagram-profile-scraper
APIFY_TIKTOK_ACTOR=clockworks/tiktok-profile-scraper
APIFY_X_ACTOR=apify/twitter-scraper
```

Token from [Apify Console](https://console.apify.com/account/integrations). When unset, each platform uses free fallback paths (shallower data).

Shared runner: `backend/pipeline/content/providers/apify_client.py`.

### scrape.do (generic pages)

```env
SCRAPE_DO_API=...
```

Used for Medium, Substack, and article roundup pages when plain `httpx` is blocked. Only applies to non-platform URLs.

### YouTube Data API v3 (optional, recommended — Plan 06 Strand A)

The YouTube provider's HTML regex path is the default and works without any keys. When `YOUTUBE_API_KEY` is set, the provider upgrades to authoritative Data API v3 calls before falling back:

```env
YOUTUBE_API_KEY=AIza...
```

| Without key | With key |
| --- | --- |
| Subscriber count from `og:description` regex (`compact_number`) | `channels.list` → `statistics.subscriberCount` |
| Per-video views/likes/comments: absent | `videos.list` (batched, ≤50 IDs) populates `post.view_count` / `like_count` / `comment_count` |
| `lifetime_views`: absent | `channels.list` → `statistics.viewCount` exposed on `raw.lifetime_views` |
| Verified badge: `"Verified" in html` substring match | `snippet.customUrl && status.isLinked` (the official signal) |
| Provider tag: `youtube` | `youtube` (with `raw.api_source = "youtube_data_v3"`) |

When the key is set but the API returns no items (channel not found, quota error, transient 5xx), the provider falls back to the HTML path and tags the result with `provider="youtube_html_fallback"` so callers can detect the degraded mode.

**Quota.** YouTube Data API v3 has a 10,000 unit/day free quota. Each Plan 06 run consumes 2 units per profile: `channels.list=1` + `videos.list=1` (≤50 IDs per call). A 50-influencer campaign = 100 units. Plan 06 reads `settings.YOUTUBE_API_KEY` (set in `backend/core/config.py:42`); the worker process needs a restart after the value changes (`docker compose restart worker_scraping worker_ai_agent backend-core`).

**How to get one.** [Google Cloud Console](https://console.cloud.google.com/) → create/select a project → enable **YouTube Data API v3** (`APIs & Services → Library`) → `APIs & Services → Credentials` → "Create Credentials" → "API key". Recommended: restrict the key to YouTube Data API v3 only.

### Semantic relevance embeddings (optional, recommended — Plan 06 Strand C)

`OPENROUTER_API_KEY` already powers chat-completions (query planning, handle verification, scoring explanation). The same key also powers the `/embeddings` route used by the relevance scorer:

```env
OPENROUTER_API_KEY=sk-or-v1-...
UMGL_EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536
```

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | (none) | When absent, embeddings are stored as deterministic hash-derived stub vectors and the relevance scorer runs cosine over the stubs (low-but-nonzero values for unrelated content). The token-overlap fallback kicks in only when one or both envelopes are missing entirely. |
| `UMGL_EMBEDDING_MODEL` | `text-embedding-3-small` | Model id passed to OpenRouter's `/embeddings` route. Any OpenAI-compatible embedding model on OpenRouter works. |
| `EMBEDDING_DIM` | `1536` | Dimension of the deterministic hash-stub vector and (must match) the embedding model's output dimension. Mismatched dims cause cosine to silently return nonsense — set this when you change models. |

**What the embedding gives you.** Without the key, the relevance scorer still runs but uses cosine over hash stubs (deterministic, cheap, but mostly noise for unrelated content). The score will be a finite float in roughly `[0, 100]`, not a neutral `50.0`, and stays stable across runs. With the key, both `Influencer.embedding` and `Campaign.embedding` are real semantic vectors and the cosine reflects actual topical overlap.

**How to get one.** [openrouter.ai/keys](https://openrouter.ai/keys). `text-embedding-3-small` is roughly $0.02 per 1M tokens; a typical campaign (50 influencers × 1 short text per side) is well under a cent.

**When does the embedding get computed?**

- Influencer: `compute_and_persist_embedding` runs at the end of `enrich_influencer_platforms_task` (`backend/pipeline/tasks/enrich.py:65`), after platform profiles are persisted.
- Campaign: `compute_and_persist_campaign_embedding` runs synchronously inside `start_campaign` (`backend/pipeline/tasks/orchestrator.py`), before the pipeline fan-out. This guarantees the score task always reads a populated `Campaign.embedding` — no race where the score runs before the embedding is ready.

A failure in either helper is logged and swallowed; the next scorer invocation falls back to token-overlap, never crashes a campaign.

### YouTube Data API v3 (optional, recommended)

```env
YOUTUBE_API_KEY=AIza...
```

When set, `fetch_youtube_profile` (`backend/pipeline/content/providers/youtube.py`) calls `channels.list` + `videos.list` and populates:

- **Authoritative subscriber count** (`statistics.subscriberCount`) instead of the HTML `og:description` regex.
- **Per-video stats** (`viewCount` / `likeCount` / `commentCount` on each post dict) — lights up `engagement_rollup.compute_recent_engagement` and the `avg_views` fallback in `enrichment.persist_enrichment` automatically, no extra wiring.
- **Verified badge** (`status.isLinked` + `snippet.customUrl`) instead of the `"Verified"` substring match.
- **Lifetime view count** (`statistics.viewCount`) — written to `PlatformProfile.raw["lifetime_views"]` and surfaced by the engagement roll-up.

When **unset**, the provider falls back to the existing HTML regex + RSS-only path — same behaviour as today.

**Quota math.** Free tier is 10,000 units/day. `channels.list` costs 1 unit, `videos.list` costs 1 unit, so each profile fetch = 2 units. A 50-influencer campaign = 100 units, leaving 9,900 units of headroom.

**Get a key.** [Google Cloud Console](https://console.cloud.google.com/) → enable the YouTube Data API v3 → APIs & Services → Credentials → Create Credentials → API key. Restrict it to the YouTube Data API v3 in production.

### Semantic relevance embeddings (optional, recommended)

```env
OPENROUTER_API_KEY=sk-or-v1-...
UMGL_EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536
```

`OPENROUTER_API_KEY` powers both the chat-completion route and OpenRouter's `/embeddings` endpoint used by `compute_and_persist_embedding` and `compute_and_persist_campaign_embedding` (`backend/pipeline/content/enrichment.py`).

When the key is **unset**, embeddings are stored as deterministic hash-derived stub vectors (L2-normalized, `EMBEDDING_DIM` long) and the relevance scorer (`backend/pipeline/fusion/sub_scores.py`) still runs cosine on them — the score will be small-but-nonzero for unrelated stubs rather than the 40-100 range produced by token-overlap. The helper **always** writes a JSONB envelope so `sub_scores.relevance_score` can detect both sides are present.

`UMGL_EMBEDDING_MODEL` is the model ID passed to the `/embeddings` route (default `text-embedding-3-small`, ~$0.02 / 1M tokens). `EMBEDDING_DIM` **must match the model's output dimension** — if it doesn't, cosine is wrong (the scorer returns `None` for dimension mismatches and falls back to token-overlap).

[Get an OpenRouter key](https://openrouter.ai/keys).

## Recommended setups

### Local development (zero search cost)

```env
APP_ENV=dev
SEARCH_PROVIDER_MODE=auto
BRAVE_SEARCH_API_KEY=
APIFY_API_TOKEN=                    # optional; improves IG/TikTok/X depth
```

With no API keys set, the pipeline falls back to synthetic discovery URLs.

### Hackathon / judges deployment

```env
APP_ENV=production
SEARCH_PROVIDER_MODE=auto
BRAVE_SEARCH_API_KEY=your-key
APIFY_API_TOKEN=your-token
SCRAPE_DO_API=                      # optional, for article sources
```

Set these in the **host environment** (Railway, Render, etc.).

## Docker services

| Service | Port | When needed |
| --- | --- | --- |
| `worker_scraping` | — | Restart after changing search/fetch env vars |

```bash
docker compose restart worker_scraping worker_ai_agent backend-core
```

## Tests

```bash
pytest backend/tests/pipeline/test_search_providers.py -v
pytest backend/tests/pipeline/test_apify_providers.py -v
pytest backend/tests/pipeline/test_role4_scraping.py -v
pytest backend/tests/pipeline/test_youtube_provider.py -v          # Plan 06 Strand A
pytest backend/tests/pipeline/test_embedding_env_wiring.py -v     # Plan 06 Strand C
```

## Related docs

- [pipeline-flow-architecture.md](./pipeline-flow-architecture.md) — end-to-end flow
- [Role-4-Pipeline-Intelligence.md](./Role-4-Pipeline-Intelligence.md) — pipeline ownership
- [development.md](./development.md) — local setup
