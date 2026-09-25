"""
AI Call Analytics — Theme Discovery Pydantic Schemas.
"""

from __future__ import annotations

import uuid
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.common import PaginationMeta


class ThemeItemResponse(BaseModel):
    """A discovered conversational theme cluster."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cluster_id: int
    title: str
    summary: str
    size: int
    top_keywords: list[str] = Field(default_factory=list)
    exemplar_turn_ids: list[int] = Field(default_factory=list)


class ThemeListResponse(BaseModel):
    """List of discovered themes for a discovery run."""

    run_id: uuid.UUID | None = None
    run_name: str | None = None
    total_themes: int
    noise_count: int | None = None
    noise_percentage: float | None = None
    silhouette_score: float | None = None
    themes: list[ThemeItemResponse]
