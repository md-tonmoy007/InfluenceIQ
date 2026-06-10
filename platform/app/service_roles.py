from __future__ import annotations

SEARCH_WORKER_SERVICE = "worker_search"
CRAWL_WORKER_SERVICE = "worker_crawl"
EXTRACT_WORKER_SERVICE = "worker_extract"
SCORE_WORKER_SERVICE = "worker_score"
AI_AGENT_SERVICE = "ai_agent_services"
SCRAPING_SERVICE = "scraping_service"
SCORING_SERVICE = "scoring_service"
BACKEND_CORE_SERVICE = "backend-core"

TASK_MODULES_BY_SERVICE = {
    SEARCH_WORKER_SERVICE: [
        "app.tasks.search",
    ],
    CRAWL_WORKER_SERVICE: [
        "app.tasks.crawl",
    ],
    EXTRACT_WORKER_SERVICE: [
        "app.tasks.extract",
    ],
    SCORE_WORKER_SERVICE: [
        "app.tasks.score",
    ],
    AI_AGENT_SERVICE: [
        "app.tasks.search",
        "app.tasks.extract",
        "app.tasks.score",
    ],
    SCRAPING_SERVICE: [
        "app.tasks.search",
        "app.tasks.crawl",
    ],
    SCORING_SERVICE: [
        "app.tasks.extract",
        "app.tasks.score",
    ],
}

TASK_QUEUE_BY_NAME = {
    "app.tasks.search.generate_queries": "search_queue",
    "app.tasks.search.execute_search": "search_queue",
    "app.tasks.crawl.fetch_page": "crawl_queue",
    "app.tasks.crawl.extract_content": "crawl_queue",
    "app.tasks.extract.extract_influencers": "extract_queue",
    "app.tasks.extract.resolve_identity_llm": "extract_queue",
    "app.tasks.score.classify_brand_safety": "score_queue",
    "app.tasks.score.score_influencer": "score_queue",
}

ALL_TASK_MODULES = sorted(
    {
        module_name
        for module_list in TASK_MODULES_BY_SERVICE.values()
        for module_name in module_list
    }
)

WORKER_QUEUES = sorted(set(TASK_QUEUE_BY_NAME.values()))
