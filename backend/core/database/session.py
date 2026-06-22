from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.core.config import settings

Base = declarative_base()

# Engine + SessionLocal are created lazily so importing this module
# does not require the configured DB driver (e.g. ``psycopg``) to be
# installed. Tests that exercise non-DB code paths can import any
# model/schema without an OS-level driver present.

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def _get_engine() -> Engine:
    """Build the engine on first access; cache thereafter."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _engine


def _get_session_local() -> sessionmaker:
    """Build the sessionmaker on first access; cache thereafter."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=_get_engine()
        )
    return _SessionLocal


def get_db() -> Generator[Any, None, None]:
    """Dependency generator for database sessions.
    Yields a session and safely closes it upon completion of request.
    """
    db = _get_session_local()()
    try:
        yield db
    finally:
        db.close()
