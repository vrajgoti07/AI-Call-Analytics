"""
AI Call Analytics — API v1 Router Aggregator.
"""

from fastapi import APIRouter

from backend.app.api.v1.analysis import router as analysis_router
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.batches import router as batches_router
from backend.app.api.v1.calls import router as calls_router
from backend.app.api.v1.evaluation import router as evaluation_router
from backend.app.api.v1.jobs import router as jobs_router
from backend.app.api.v1.reports import router as reports_router
from backend.app.api.v1.risk import router as risk_router
from backend.app.api.v1.search import router as search_router
from backend.app.api.v1.themes import router as themes_router
from backend.app.api.v1.transcript import router as transcript_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(batches_router)
api_v1_router.include_router(calls_router)
api_v1_router.include_router(transcript_router)
api_v1_router.include_router(analysis_router)
api_v1_router.include_router(risk_router)
api_v1_router.include_router(themes_router)
api_v1_router.include_router(search_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(evaluation_router)
api_v1_router.include_router(reports_router)

__all__ = ["api_v1_router"]
