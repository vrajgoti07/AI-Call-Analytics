"""
AI Call Analytics — FastAPI Application Entry Point.

Creates the FastAPI application with security middleware, request correlation,
health endpoints (liveness & readiness), global exception handlers, and v1 routes.
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

# Ensure both project root and backend dir are in sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
for _p in [str(_PROJECT_ROOT), str(_BACKEND_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend.app.api.v1 import api_v1_router
from backend.app.core.config import settings, validate_environment
from backend.app.core.exceptions import register_exception_handlers
from backend.app.core.logging import setup_logging
from backend.app.core.middleware import (
    RequestCorrelationMiddleware,
    SecurityHeadersMiddleware,
)
from backend.app.database.session import sync_engine

logger = setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup validation and graceful shutdown."""
    logger.info("Validating environment for %s [%s]", settings.app_name, settings.app_env)
    validate_environment(settings)
    logger.info("AI Call Analytics backend started successfully on env=%s", settings.app_env)
    yield
    logger.info("Shutting down AI Call Analytics backend")


app = FastAPI(
    title="AI Call Analytics API",
    description="AI-powered customer support call analytics platform.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ---- Middleware Pipeline ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestCorrelationMiddleware)

# ---- Exception Handlers ----
register_exception_handlers(app)

# ---- API v1 Routes ----
app.include_router(api_v1_router)


# ---- Health Endpoints ----
@app.get("/health", tags=["health"], summary="Service health status")
async def health_check() -> dict:
    """Basic health check indicating process status."""
    return {
        "status": "ok",
        "service": "ai-call-analytics-backend",
        "environment": settings.app_env,
        "version": "1.0.0",
    }


@app.get("/health/live", tags=["health"], summary="Liveness probe")
async def liveness_probe() -> dict:
    """Liveness probe confirming the HTTP server is alive and accepting traffic."""
    return {"status": "alive"}


@app.get("/health/ready", tags=["health"], summary="Readiness probe")
async def readiness_probe(response: Response) -> dict:
    """
    Readiness probe testing connectivity to critical dependencies:
    - PostgreSQL database
    - Redis cache / broker
    """
    db_ok = False
    redis_ok = False
    details: dict[str, str] = {}

    # Test PostgreSQL
    try:
        with sync_engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
            db_ok = True
            details["database"] = "connected"
    except Exception as e:
        logger.warning("Readiness probe DB connection failure: %s", e)
        details["database"] = f"error: {e}"

    # Test Redis
    try:
        import redis
        r = redis.from_url(settings.resolved_redis_url, socket_timeout=2.0)
        if r.ping():
            redis_ok = True
            details["redis"] = "connected"
        else:
            details["redis"] = "ping_failed"
    except Exception as e:
        logger.warning("Readiness probe Redis connection failure: %s", e)
        details["redis"] = f"error: {e}"

    overall_ready = db_ok and redis_ok
    if not overall_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if overall_ready else "not_ready",
        "dependencies": details,
    }
