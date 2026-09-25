"""
AI Call Analytics — Escalation Risk Pydantic Schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class EscalationRiskResponse(BaseModel):
    """Escalation risk assessment evaluation for a call."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    call_id: str
    risk_score: float
    risk_probability: float
    risk_level: str
    model_type: str
    model_name: str
    model_version: str
    explanation: str
    top_factors: list[dict[str, Any]] = Field(default_factory=list)
    temporal_risk: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
