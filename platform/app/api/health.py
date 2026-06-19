from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.db.session import get_db
from app.services.redis_client import redis_client

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def get_health(db: Session = Depends(get_db)) -> dict:
    """Returns application integration health, Celery worker counts, and queue depths."""
    queues = ["search_queue", "crawl_queue", "extract_queue", "score_queue"]
    
    # Fetch queue depths from Redis
    queue_depths = {}
    for q in queues:
        try:
            queue_depths[q] = redis_client.llen(q)
        except Exception:
            queue_depths[q] = 0

    # PostgreSQL database connectivity status
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "down"

    # Redis state cache connectivity status
    try:
        redis_client.ping()
        redis_status = "connected"
    except Exception:
        redis_status = "down"

    # Celery active task status and worker counts
    workers = {}
    try:
        inspect = celery_app.control.inspect(timeout=0.5)
        active = inspect.active() or {} if inspect else {}
        workers = {name: len(tasks) for name, tasks in active.items()}
    except Exception:
        pass  # Fail gracefully if Celery inspector timeout or offline

    is_healthy = db_status == "connected" and redis_status == "connected"

    return {
        "status": "ok" if is_healthy else "degraded",
        "queues": queue_depths,
        "workers": workers,
        "db": db_status,
        "redis": redis_status,
    }
