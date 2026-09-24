"""
AI Call Analytics — FastAPI Application Entry Point.

Creates the FastAPI application with middleware, health endpoint,
and lifespan event handlers.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import sys
from pathlib import Path

# Ensure both project root and backend dir are in sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
for _p in [str(_PROJECT_ROOT), str(_BACKEND_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from backend.app.core.config import settings
    from backend.app.core.logging import setup_logging
except ModuleNotFoundError:
    from app.core.config import settings
    from app.core.logging import setup_logging

logger = setup_logging("DEBUG" if settings.debug else "INFO")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown events."""
    logger.info("Starting AI Call Analytics backend — env=%s", settings.app_env)
    yield
    logger.info("Shutting down AI Call Analytics backend")


app = FastAPI(
    title="AI Call Analytics API",
    description="AI-powered customer support call analytics platform.",
    version="0.1.0",
    lifespan=lifespan,
)

# ---- CORS Middleware ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Health Endpoint ----
@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns:
        JSON with status and service name.
    """
    return {
        "status": "ok",
        "service": "ai-call-analytics-backend",
    }
