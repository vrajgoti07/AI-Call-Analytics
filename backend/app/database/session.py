"""
AI Call Analytics — Database Session & Engine Configuration.

Configures synchronous SQLAlchemy engine and session factories with connection pooling
and transactional session lifecycle management.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import settings

# Synchronous Engine bound to settings
sync_engine = create_engine(
    settings.sync_database_url,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
)

SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    Provide a transactional database session generator with automatic rollback on error.
    """
    session = SyncSessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
