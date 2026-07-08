from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[1] / ".env"),
        extra="ignore",
    )

    APP_ENV: str = "dev"
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str
    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    REDIS_STATE_DB: str

    QDRANT_URL: str
    QDRANT_API_KEY: str = ""

    MOONSHOT_API_KEY: str = ""
    KIMI_MODEL: str = "kimi-k2"
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-v4"
    OPENAI_API_KEY: str = ""
    OPENAI_JUDGE_MODEL: str = "gpt-4o-mini"
    OPENAI_ESCALATION_MODEL: str = "gpt-5-mini"

    SERP_API_KEY: str = ""
    BRAVE_SEARCH_API_KEY: str = ""
    # auto | brave | serpapi | all (merge every configured provider)
    SEARCH_PROVIDER_MODE: str = "auto"
    SCRAPE_DO_API: str = ""

    YOUTUBE_API_KEY: str = ""
    APIFY_API_TOKEN: str = ""
    APIFY_INSTAGRAM_ACTOR: str = "apify/instagram-profile-scraper"
    APIFY_TIKTOK_ACTOR: str = "clockworks/tiktok-profile-scraper"
    APIFY_X_ACTOR: str = "apify/twitter-scraper"
    APIFY_INSTAGRAM_COMMENTS_ACTOR: str = "apify/instagram-comment-scraper"
    APIFY_TIKTOK_COMMENTS_ACTOR: str = "clockworks/tiktok-comments-scraper"
    PLATFORM_COMMENT_LIMIT: int = 200
    PLATFORM_POST_LIMIT: int = 20
    DEEP_ANALYSIS_COMMENT_TARGET: int = 2000
    ALLOW_SYNTHETIC_FETCH_FALLBACK: bool = False

    COMMENT_FETCH_ON_ENRICH: bool = True
    ENRICH_COMMENT_POST_LIMIT: int = 3
    ENRICH_COMMENTS_PER_POST: int = 50
    YOUTUBE_COMMENTS_PER_POST: int = 100
    COMMENT_CACHE_TTL_SECONDS: int = 6 * 60 * 60
    # Wall-clock budgets (seconds) that bound the HTTP-heavy enrichment loops so
    # one influencer with many URLs/posts can never pin a scraping-worker slot
    # long enough to stall the queue. Each individual provider call is already
    # bounded by httpx timeouts; these cap the *loops* over calls. Kept well
    # under the enrich task's 300s soft_time_limit so they are the primary
    # mechanism and the soft limit is only a last-resort backstop.
    ENRICH_PROFILE_FETCH_BUDGET_SEC: float = 120.0
    ENRICH_COMMENT_FETCH_BUDGET_SEC: float = 90.0

    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 1536
    # Preferred name (Plan 06); ML adapters read UMGL_EMBEDDING_MODEL.
    UMGL_EMBEDDING_MODEL: str = "text-embedding-3-small"

    TOKEN_BUDGET_QUERY_GEN: int = 2000
    TOKEN_BUDGET_BRAND_SAFETY: int = 800
    TOKEN_BUDGET_IDENTITY_RESOLUTION: int = 400
    TOKEN_BUDGET_SCORE_EXPLAIN: int = 1500

    SCORE_VERSION: str = "v1.0"
    CONFIDENCE_CAP_THRESHOLD: int = 3
    CONFIDENCE_CAP_VALUE: int = 70

    # Auth / JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Stripe Billing (optional — billing endpoints return 503 when unset)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_GROWTH_MONTHLY: str = ""
    STRIPE_PRICE_GROWTH_ANNUAL: str = ""
    FRONTEND_URL: str = "http://localhost:3000"


settings = Settings()
