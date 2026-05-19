from __future__ import annotations

import redis
from fastapi import FastAPI
from sqlalchemy import create_engine, text

from app.celery_app import celery_app
from app.config import settings

app = FastAPI(title="InfluenceIQ", version="0.1.0")

_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
_redis = redis.from_url(settings.REDIS_URL)


@app.get("/health")
def health() -> dict:
    queues = ["search_queue", "crawl_queue", "extract_queue", "score_queue"]
    queue_depths = {q: _redis.llen(q) for q in queues}

    try:
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "down"

    try:
        _redis.ping()
        redis_status = "connected"
    except Exception:
        redis_status = "down"

    inspect = celery_app.control.inspect(timeout=1)
    active = inspect.active() or {}
    workers = {name: len(tasks) for name, tasks in active.items()}

    return {
        "status": "ok" if db_status == "connected" and redis_status == "connected" else "degraded",
        "queues": queue_depths,
        "workers": workers,
        "db": db_status,
        "redis": redis_status,
    }


@app.get("/")
def root() -> dict:
    return {"service": "influenceiq", "version": app.version}
