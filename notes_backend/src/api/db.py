"""
Database adapter for the notes backend (SQLite via SQLAlchemy).

We use SQLAlchemy ORM with a single SQLite file configured via env var.

Env:
- SQLITE_DB: path to SQLite DB file (required at runtime; provided by the database container).
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# NOTE: do not hardcode; rely on env var injected by runtime/container.
_SQLITE_DB_PATH = os.environ.get("SQLITE_DB")

if not _SQLITE_DB_PATH:
    # Raise at import time so misconfiguration is immediately visible in logs/CI.
    raise RuntimeError(
        "Missing required environment variable SQLITE_DB (path to sqlite database file)."
    )

# check_same_thread=False is required for SQLite when used with FastAPI dependency injection
# across different threads.
DATABASE_URL = f"sqlite:///{_SQLITE_DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# PUBLIC_INTERFACE
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a SQLAlchemy session.

    Yields:
        Session: An active SQLAlchemy ORM session.

    Guarantees:
        - The session is closed after request handling completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager for internal scripts/one-offs (not used by routes)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
