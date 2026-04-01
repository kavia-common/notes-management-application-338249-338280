"""
Database initialization.

We create tables at startup for this lightweight app (SQLite).
"""

from __future__ import annotations

import logging

from src.api.db import engine
from src.api.models import Base

logger = logging.getLogger("notes_backend.init_db")


# PUBLIC_INTERFACE
def init_db() -> None:
    """Initialize the SQLite schema (create tables if they do not exist)."""
    logger.info("Initializing database schema (create_all)")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized")
