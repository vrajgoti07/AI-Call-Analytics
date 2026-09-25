"""
AI Call Analytics — Escalation Risk ORM Model.

Persists call-level escalation risk evaluations, factor contributions,
temporal trajectory points, and feature snapshots in PostgreSQL.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, Index, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class EscalationRisk(Base):
    """
    ORM representation of a call escalation risk analysis result.
    Captures multi-modal risk scoring, classification tiers, explainability factors,
    and historical feature snapshots for monitoring and auditability.
    """

    __tablename__ = "escalation_risks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    call_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # Model and feature metadata
    model_type: Mapped[str] = mapped_column(String(32), nullable=False, default="heuristic")
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    feature_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    threshold_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1.0")

    # Risk Metrics
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    risk_probability: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # Explainability & Telemetry (JSON / Text)
    top_factors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    feature_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    temporal_risk: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

    # Operational Telemetry
    processing_time_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    metadata_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        Index("ix_escalation_risks_call_id_created_at", "call_id", "created_at"),
        Index("ix_escalation_risks_risk_level_score", "risk_level", "risk_score"),
    )

    def __repr__(self) -> str:
        return (
            f"<EscalationRisk(id={self.id}, call_id='{self.call_id}', "
            f"score={self.risk_score:.1f}, level='{self.risk_level}', "
            f"model_type='{self.model_type}')>"
        )
