from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.core.config import settings

# Create synchronous engine with pool connection checking
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[SessionLocal, None, None]:
    """Dependency generator for database sessions.
    Yields a session and safely closes it upon completion of request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
