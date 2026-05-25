from __future__ import annotations

AI_AGENT_SERVICE = "ai_agent_services"
SCRAPING_SERVICE = "scraping_service"
SCORING_SERVICE = "scoring_service"
BACKEND_CORE_SERVICE = "backend-core"

TASK_MODULES_BY_SERVICE = {
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
    "app.tasks.search.generate_queries": "ai_agent_queue",
    "app.tasks.extract.resolve_identity_llm": "ai_agent_queue",
    "app.tasks.score.classify_brand_safety": "ai_agent_queue",
    "app.tasks.search.execute_search": "scraping_queue",
    "app.tasks.crawl.fetch_page": "scraping_queue",
    "app.tasks.crawl.extract_content": "scraping_queue",
    "app.tasks.extract.extract_influencers": "scoring_queue",
    "app.tasks.score.score_influencer": "scoring_queue",
}

ALL_TASK_MODULES = sorted(
    {
        module_name
        for module_list in TASK_MODULES_BY_SERVICE.values()
        for module_name in module_list
    }
)

WORKER_QUEUES = sorted(set(TASK_QUEUE_BY_NAME.values()))
