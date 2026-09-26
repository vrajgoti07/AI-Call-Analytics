"""
AI Call Analytics — Theme Discovery API Router.

Endpoints for retrieving persisted theme discovery runs and clusters,
scoped strictly to the user's company workspace.
"""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.auth import get_current_user
from backend.app.core.exceptions import AppException
from backend.app.database.session import get_db
from backend.app.models.theme import Theme, ThemeDiscoveryRun
from backend.app.models.user import User
from backend.app.schemas.theme import ThemeItemResponse, ThemeListResponse

router = APIRouter(prefix="/themes", tags=["themes"])


@router.get(
    "",
    response_model=ThemeListResponse,
    summary="List persisted theme discovery clusters",
)
def list_themes(
    run_id: uuid.UUID | None = Query(default=None, description="Optional filter by discovery run ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ThemeListResponse:
    """Retrieve persisted conversational themes and cluster summaries from Phase 7."""
    run: ThemeDiscoveryRun | None = None
    if run_id:
        run = db.scalar(select(ThemeDiscoveryRun).where(ThemeDiscoveryRun.id == run_id))
    else:
        run = db.scalar(
            select(ThemeDiscoveryRun)
            .order_by(ThemeDiscoveryRun.created_at.desc())
            .limit(1)
        )

    if not run:
        return ThemeListResponse(
            run_id=None,
            run_name=None,
            total_themes=0,
            themes=[],
        )

    themes_stmt = select(Theme).where(Theme.run_id == run.id).order_by(Theme.cluster_id.asc())
    theme_records = list(db.scalars(themes_stmt))

    return ThemeListResponse(
        run_id=run.id,
        run_name=run.run_name,
        total_themes=len(theme_records),
        noise_count=run.noise_count,
        noise_percentage=run.noise_percentage,
        silhouette_score=run.silhouette_score,
        themes=[ThemeItemResponse.model_validate(t) for t in theme_records],
    )


@router.get(
    "/{theme_id}",
    response_model=ThemeItemResponse,
    summary="Retrieve individual theme details",
)
def get_theme(
    theme_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ThemeItemResponse:
    """Retrieve specific theme cluster details and keywords."""
    theme = db.scalar(select(Theme).where(Theme.id == theme_id))
    if not theme:
        raise AppException(
            code="THEME_NOT_FOUND",
            message=f"Theme cluster '{theme_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return ThemeItemResponse.model_validate(theme)
