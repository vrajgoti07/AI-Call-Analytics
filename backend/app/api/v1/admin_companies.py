"""
AI Call Analytics — Admin Companies Management API Router.

Strictly restricted to platform ADMIN role. Provides endpoints for inspecting
and managing registered company workspaces, including status activation/deactivation.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.auth import require_admin
from backend.app.core.exceptions import CompanyNotFoundError
from backend.app.database.session import get_db
from backend.app.models.call import Call
from backend.app.models.company import Company
from backend.app.models.ingestion_batch import IngestionBatch
from backend.app.models.user import User

router = APIRouter(prefix="/admin/companies", tags=["admin-companies"])


class AdminCompanyItem(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    user_count: int = 0
    call_count: int = 0
    batch_count: int = 0


class AdminCompanyStatusUpdate(BaseModel):
    is_active: bool = Field(..., description="Target active status for company")


@router.get(
    "",
    response_model=list[AdminCompanyItem],
    summary="List all company workspaces with resource counts (Admin only)",
)
def list_admin_companies(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AdminCompanyItem]:
    """Retrieve full company inventory for platform administrator."""
    companies = db.scalars(select(Company).order_by(Company.created_at.desc())).all()

    items = []
    for c in companies:
        user_count = db.scalar(
            select(func.count(User.id)).where(User.company_id == c.id)
        ) or 0
        call_count = db.scalar(
            select(func.count(Call.id)).where(Call.company_id == c.id)
        ) or 0
        batch_count = db.scalar(
            select(func.count(IngestionBatch.id)).where(IngestionBatch.company_id == c.id)
        ) or 0

        items.append(
            AdminCompanyItem(
                id=c.id,
                name=c.name,
                slug=c.slug,
                is_active=c.is_active,
                created_at=c.created_at,
                updated_at=c.updated_at,
                user_count=user_count,
                call_count=call_count,
                batch_count=batch_count,
            )
        )

    return items


@router.patch(
    "/{company_id}/status",
    response_model=AdminCompanyItem,
    summary="Activate or deactivate a company workspace (Admin only)",
)
def update_company_status(
    company_id: uuid.UUID,
    payload: AdminCompanyStatusUpdate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminCompanyItem:
    """Toggle company active status. Deactivating bars company users from accessing protected APIs."""
    company = db.get(Company, company_id)
    if not company:
        raise CompanyNotFoundError(company_id)

    company.is_active = payload.is_active
    db.commit()
    db.refresh(company)

    user_count = db.scalar(
        select(func.count(User.id)).where(User.company_id == company.id)
    ) or 0
    call_count = db.scalar(
        select(func.count(Call.id)).where(Call.company_id == company.id)
    ) or 0
    batch_count = db.scalar(
        select(func.count(IngestionBatch.id)).where(IngestionBatch.company_id == company.id)
    ) or 0

    return AdminCompanyItem(
        id=company.id,
        name=company.name,
        slug=company.slug,
        is_active=company.is_active,
        created_at=company.created_at,
        updated_at=company.updated_at,
        user_count=user_count,
        call_count=call_count,
        batch_count=batch_count,
    )
