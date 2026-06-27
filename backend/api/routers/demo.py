from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.database.session import get_db
from backend.demo import reset_database, run_query_generation, run_scrape, run_search_filter, seed_database
from backend.demo.schemas import QueryGenRequest, ScrapeRequest, SearchFilterRequest

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/query-gen", response_model=dict[str, Any])
def test_query_generation(req: QueryGenRequest) -> dict[str, Any]:
    try:
        return run_query_generation(req)
    except Exception as exc:  # noqa: BLE001 — diagnostics endpoint
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/search-filter", response_model=dict[str, Any])
def test_search_filter(req: SearchFilterRequest) -> dict[str, Any]:
    try:
        return run_search_filter(req)
    except Exception as exc:  # noqa: BLE001 — diagnostics endpoint
        raise HTTPException(status_code=502, detail=f"search_web failed: {exc}") from exc


@router.post("/scrape", response_model=dict[str, Any])
def test_scrape(req: ScrapeRequest) -> dict[str, Any]:
    try:
        return run_scrape(req)
    except Exception as exc:  # noqa: BLE001 — diagnostics endpoint
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/reset", response_model=dict[str, str])
def reset_demo_database(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        reset_database(db)
        return {"status": "ok", "message": "Database reset completed successfully."}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database reset failed: {exc}") from exc


@router.post("/seed", response_model=dict[str, Any])
def seed_demo_database(db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        return seed_database(db)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database seed failed: {exc}") from exc
