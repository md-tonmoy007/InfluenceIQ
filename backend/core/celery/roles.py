from __future__ import annotations

AI_AGENT = "ai_agent"
SCRAPING = "scraping"
SCORING = "scoring"

TASK_QUEUE_BY_NAME: dict[str, str] = {
    # ai_agent — LLM-heavy tasks
    "backend.pipeline.tasks.search.generate_queries": "ai_agent_queue",
    "backend.pipeline.tasks.extract.resolve_identity_llm": "ai_agent_queue",
    "backend.pipeline.tasks.score.classify_brand_safety": "ai_agent_queue",
    # scraping — I/O-heavy tasks (search + crawl)
    "backend.pipeline.tasks.search.execute_search": "scraping_queue",
    "backend.pipeline.tasks.crawl.fetch_page": "scraping_queue",
    "backend.pipeline.tasks.crawl.extract_content": "scraping_queue",
    # scoring — compute-heavy tasks (extraction + scoring)
    "backend.pipeline.tasks.extract.extract_influencers": "scoring_queue",
    "backend.pipeline.tasks.extract.resolve_identity_cluster": "scoring_queue",
    "backend.pipeline.tasks.score.score_influencer": "scoring_queue",
}

TASK_NAMES_BY_SERVICE: dict[str, list[str]] = {
    AI_AGENT: [
        "backend.pipeline.tasks.search.generate_queries",
        "backend.pipeline.tasks.extract.resolve_identity_llm",
        "backend.pipeline.tasks.score.classify_brand_safety",
    ],
    SCRAPING: [
        "backend.pipeline.tasks.search.execute_search",
        "backend.pipeline.tasks.crawl.fetch_page",
        "backend.pipeline.tasks.crawl.extract_content",
    ],
    SCORING: [
        "backend.pipeline.tasks.extract.extract_influencers",
        "backend.pipeline.tasks.extract.resolve_identity_cluster",
        "backend.pipeline.tasks.score.score_influencer",
    ],
}

WORKER_QUEUES: list[str] = sorted(set(TASK_QUEUE_BY_NAME.values()))
