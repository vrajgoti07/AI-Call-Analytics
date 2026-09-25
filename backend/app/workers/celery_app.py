"""
AI Call Analytics — Celery Application Configuration.

Configures Celery worker with Redis broker, task serialization, idempotency settings,
and task registration.
"""

from __future__ import annotations

import os
from celery import Celery

from backend.app.core.config import settings

celery_app = Celery(
    "ai_call_analytics",
    broker=settings.resolved_celery_broker_url,
    backend=settings.resolved_celery_result_backend,
    include=["backend.app.workers.pipeline_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    result_expires=86400,  # 24 hours
    task_time_limit=settings.celery_task_timeout,
    task_soft_time_limit=settings.celery_task_timeout - 60,
)

# Auto-register pipeline tasks
import backend.app.workers.pipeline_tasks  # noqa: F401

