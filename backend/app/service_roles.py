from __future__ import annotations

AI_AGENT_SERVICE = "ai_agent_service"
SCRAPING_SERVICE = "scraping_service"
SCORING_SERVICE = "scoring_service"

TASK_QUEUE_BY_NAME: dict[str, str] = {
    # ai_agent_service — LLM-heavy tasks
    "app.tasks.search.generate_queries": "ai_agent_queue",
    "app.tasks.extract.resolve_identity_llm": "ai_agent_queue",
    "app.tasks.score.classify_brand_safety": "ai_agent_queue",
    # scraping_service — I/O-heavy tasks (search + crawl)
    "app.tasks.search.execute_search": "scraping_queue",
    "app.tasks.crawl.fetch_page": "scraping_queue",
    "app.tasks.crawl.extract_content": "scraping_queue",
    # scoring_service — compute-heavy tasks (extraction + scoring)
    "app.tasks.extract.extract_influencers": "scoring_queue",
    "app.tasks.score.score_influencer": "scoring_queue",
}

TASK_NAMES_BY_SERVICE: dict[str, list[str]] = {
    AI_AGENT_SERVICE: [
        "app.tasks.search.generate_queries",
        "app.tasks.extract.resolve_identity_llm",
        "app.tasks.score.classify_brand_safety",
    ],
    SCRAPING_SERVICE: [
        "app.tasks.search.execute_search",
        "app.tasks.crawl.fetch_page",
        "app.tasks.crawl.extract_content",
    ],
    SCORING_SERVICE: [
        "app.tasks.extract.extract_influencers",
        "app.tasks.score.score_influencer",
    ],
}

WORKER_QUEUES: list[str] = sorted(set(TASK_QUEUE_BY_NAME.values()))
