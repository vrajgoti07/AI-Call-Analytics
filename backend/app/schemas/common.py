"""
AI Call Analytics — Common API Schemas.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class PaginationMeta(BaseModel):
    """Metadata for paginated API responses."""

    total: int = Field(..., description="Total number of items matching query")
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")


class ErrorDetail(BaseModel):
    """Detailed error object returned on API failures."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable explanation of error")
    request_id: str | None = Field(default=None, description="Correlation Request ID")
    details: Any | None = Field(default=None, description="Optional extra validation context")


class ErrorResponse(BaseModel):
    """Standardized top-level API error response."""

    error: ErrorDetail
