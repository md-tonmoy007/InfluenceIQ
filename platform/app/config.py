from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "dev"
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str
    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    REDIS_STATE_DB: str

    QDRANT_URL: str
    QDRANT_API_KEY: str = ""

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    GENERATE_QUERY_AI_PROVIDER: str = "openrouter"
    GENERATE_QUERY_AI_MODEL: str = "openai/gpt-4o-mini"
    CLASSIFY_BRAND_SAFETY_AI_PROVIDER: str = ""
    CLASSIFY_BRAND_SAFETY_AI_MODEL: str = ""
    RESOLVE_IDENTITY_AI_PROVIDER: str = ""
    RESOLVE_IDENTITY_AI_MODEL: str = ""
    SCORE_EXPLAIN_AI_PROVIDER: str = ""
    SCORE_EXPLAIN_AI_MODEL: str = ""

    MOONSHOT_API_KEY: str = ""
    KIMI_MODEL: str = "kimi-k2"
    GOOGLE_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-v4"
    OPENAI_API_KEY: str = ""
    OPENAI_JUDGE_MODEL: str = "gpt-4o-mini"
    OPENAI_ESCALATION_MODEL: str = "gpt-5-mini"

    BRAVE_SEARCH_API_KEY: str = ""
    SERP_API_KEY: str = ""
    OPENSERP_URL: str = ""
    OPENSERP_API_KEY: str = ""
    SCRAPE_DO_API_KEY: str = ""
    SCRAPE_DO_BASE_URL: str = "https://api.scrape.do/"
    SEARCH_RESULT_LIMIT: int = 8
    URL_CACHE_TTL_SECONDS: int = 48 * 60 * 60
    CRAWL_MAX_DEPTH: int = 2
    CRAWL_MAX_URLS_PER_CAMPAIGN: int = 100
    CRAWL_DEFAULT_MIN_INTERVAL_SECONDS: float = 1.0
    CRAWL_SOCIAL_MIN_INTERVAL_SECONDS: float = 2.0
    CRAWL_MAX_RETRIES: int = 3
    CRAWL_BACKOFF_SECONDS: float = 2.0
    CRAWL_BACKOFF_MAX_SECONDS: float = 60.0
    YOUTUBE_API_KEY: str = ""

    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 1536

    TOKEN_BUDGET_QUERY_GEN: int = 2000
    TOKEN_BUDGET_BRAND_SAFETY: int = 800
    TOKEN_BUDGET_IDENTITY_RESOLUTION: int = 400
    TOKEN_BUDGET_SCORE_EXPLAIN: int = 1500

    SCORE_VERSION: str = "v1.0"
    CONFIDENCE_CAP_THRESHOLD: int = 3
    CONFIDENCE_CAP_VALUE: int = 70

    AUTH_SECRET_KEY: str = "dev-insecure-change-me"
    AUTH_COOKIE_NAME: str = "influenceiq_session"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    AUTH_COOKIE_SECURE: bool = False


settings = Settings()
