"""
AI Call Analytics — Theme Discovery API Router.

Endpoints for retrieving persisted theme discovery runs and clusters,
scoped strictly to the user's company workspace.
"""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.auth import get_current_user
from backend.app.core.exceptions import AppException
from backend.app.database.session import get_db
from backend.app.models.call import Call
from backend.app.models.theme import Theme, ThemeDiscoveryRun, ThemeMembership
from backend.app.models.user import User, UserRole
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
    """Retrieve persisted conversational themes and cluster summaries."""
    if current_user.role == UserRole.COMPANY.value:
        company_calls_stmt = select(Call.id).where(Call.company_id == current_user.company_id)
        company_call_ids = [str(cid) for cid in db.scalars(company_calls_stmt).all()]
        if not company_call_ids:
            return ThemeListResponse(
                run_id=None,
                run_name=None,
                total_themes=0,
                themes=[],
            )

        theme_ids_stmt = (
            select(ThemeMembership.theme_id)
            .where(
                ThemeMembership.call_id.in_(company_call_ids),
                ThemeMembership.theme_id.isnot(None),
            )
            .distinct()
        )
        allowed_theme_ids = [tid for tid in db.scalars(theme_ids_stmt).all() if tid is not None]
        if not allowed_theme_ids:
            return ThemeListResponse(
                run_id=None,
                run_name=None,
                total_themes=0,
                themes=[],
            )

        themes_stmt = select(Theme).where(Theme.id.in_(allowed_theme_ids)).order_by(Theme.cluster_id.asc())
        theme_records = list(db.scalars(themes_stmt))
        first_theme = theme_records[0] if theme_records else None
        return ThemeListResponse(
            run_id=first_theme.run_id if first_theme else None,
            run_name=first_theme.run.run_name if first_theme and first_theme.run else None,
            total_themes=len(theme_records),
            themes=[ThemeItemResponse.model_validate(t) for t in theme_records],
        )

    # ADMIN: system-wide themes
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

    if current_user.role == UserRole.COMPANY.value:
        company_calls_stmt = select(Call.id).where(Call.company_id == current_user.company_id)
        company_call_ids = [str(cid) for cid in db.scalars(company_calls_stmt).all()]
        membership_count = db.scalar(
            select(func.count(ThemeMembership.id)).where(
                ThemeMembership.theme_id == theme.id,
                ThemeMembership.call_id.in_(company_call_ids),
            )
        ) or 0
        if membership_count == 0:
            raise AppException(
                code="THEME_NOT_FOUND",
                message=f"Theme cluster '{theme_id}' was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

    return ThemeItemResponse.model_validate(theme)
