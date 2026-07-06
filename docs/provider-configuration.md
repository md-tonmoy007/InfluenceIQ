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
