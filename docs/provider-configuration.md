# Search and platform provider configuration

How InfluenceIQ chooses external services for **web search** (discovery) and **profile fetch** (per-platform scraping). All keys live in `backend/.env` (copy from `backend/.env.example`).

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
```

## Related docs

- [pipeline-flow-architecture.md](./pipeline-flow-architecture.md) — end-to-end flow
- [Role-4-Pipeline-Intelligence.md](./Role-4-Pipeline-Intelligence.md) — pipeline ownership
- [development.md](./development.md) — local setup
