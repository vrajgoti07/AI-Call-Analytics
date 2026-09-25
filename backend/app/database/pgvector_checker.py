"""
AI Call Analytics — pgvector Extension Availability & Verification Utility (Step 2, 40).

Verifies whether the target PostgreSQL instance has the pgvector extension installed,
enabled, and ready for high-dimensional vector similarity operations.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

class PgVectorUnavailable(Exception):
    """
    Raised when the pgvector extension is not installed or enabled in PostgreSQL.
    Signals that vector database capabilities are unavailable in the current environment.
    """
    pass


logger = logging.getLogger("ai_call_analytics.database.pgvector")


_cached_pgvector_status: bool | None = None


def check_pgvector_availability(
    engine: Engine,
    raise_on_error: bool = False,
    auto_create: bool = True,
    force_refresh: bool = False,
) -> bool:
    """
    Check if the pgvector extension is available and enabled in PostgreSQL.

    Args:
        engine: Active SQLAlchemy Engine.
        raise_on_error: If True, raises PgVectorUnavailable on failure.
        auto_create: If True, executes 'CREATE EXTENSION IF NOT EXISTS vector'.
        force_refresh: If True, forces re-checking database.

    Returns:
        True if pgvector is available and ready, False otherwise.
    """
    global _cached_pgvector_status
    if _cached_pgvector_status is not None and not force_refresh:
        if raise_on_error and not _cached_pgvector_status:
            raise PgVectorUnavailable("pgvector extension is not available in the database.")
        return _cached_pgvector_status

    try:
        with engine.connect() as conn:
            # 1. Attempt to create extension if requested
            if auto_create:
                try:
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                    conn.commit()
                except Exception as err:
                    logger.debug("Automatic CREATE EXTENSION vector failed: %s", err)
                    conn.rollback()

            # 2. Check if extension exists in pg_extension
            result = conn.execute(
                text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';")
            ).fetchone()

            if result:
                logger.info("pgvector extension verified: version=%s", result[1])
                _cached_pgvector_status = True
                return True

            # 3. Check if available in pg_available_extensions
            avail = conn.execute(
                text("SELECT name, default_version FROM pg_available_extensions WHERE name = 'vector';")
            ).fetchone()

            if avail:
                msg = (
                    f"pgvector extension is available (version {avail[1]}) "
                    "but has not been enabled with 'CREATE EXTENSION vector;'."
                )
            else:
                msg = (
                    "pgvector extension is NOT installed in the active PostgreSQL instance. "
                    "Ensure you are running the 'pgvector/pgvector:pg16' Docker container or have "
                    "installed the pgvector binaries."
                )

            logger.warning(msg)
            _cached_pgvector_status = False
            if raise_on_error:
                raise PgVectorUnavailable(msg)
            return False

    except PgVectorUnavailable:
        _cached_pgvector_status = False
        raise
    except Exception as err:
        _cached_pgvector_status = False
        err_msg = f"Database connection or pgvector check failed: {err}"
        logger.warning(err_msg)
        if raise_on_error:
            raise PgVectorUnavailable(err_msg) from err
        return False
