"""
AI Call Analytics — Escalation Risk API Router.

Endpoints for retrieving persisted escalation risk evaluations.
"""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.exceptions import AppException, CallNotFoundError
from backend.app.database.session import get_db
from backend.app.models.escalation import EscalationRisk
from backend.app.repositories.call_repository import CallRepository
from backend.app.schemas.risk import EscalationRiskResponse

router = APIRouter(prefix="/calls", tags=["risk"])


@router.get(
    "/{call_id}/risk",
    response_model=EscalationRiskResponse,
    summary="Retrieve escalation risk evaluation for a call",
)
def get_escalation_risk(
    call_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> EscalationRiskResponse:
    """Retrieve persisted multi-modal risk score, probability, and explainability factors."""
    call = CallRepository.get_by_id(db, call_id)
    if not call:
        raise CallNotFoundError(call_id)

    stmt = (
        select(EscalationRisk)
        .where(EscalationRisk.call_id == str(call_id))
        .order_by(EscalationRisk.created_at.desc())
        .limit(1)
    )
    risk_record = db.scalar(stmt)
    if not risk_record:
        raise AppException(
            code="RISK_NOT_FOUND",
            message=f"No escalation risk assessment found for call '{call_id}'.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return EscalationRiskResponse.model_validate(risk_record)
