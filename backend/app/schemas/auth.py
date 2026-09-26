"""
AI Call Analytics — Authentication & Company Pydantic Schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CompanyBase(BaseModel):
    """Base company properties."""

    name: str = Field(..., min_length=2, max_length=128, description="Company or organization name")


class CompanyCreate(CompanyBase):
    """Payload to create a new company/workspace."""

    pass


class CompanyResponse(CompanyBase):
    """Company public representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserBase(BaseModel):
    """Base user properties."""

    email: EmailStr = Field(..., description="User corporate or personal email")
    full_name: str = Field(..., min_length=2, max_length=128, description="Full display name")


class RegisterRequest(BaseModel):
    """Payload for user and workspace self-registration."""

    email: EmailStr = Field(..., description="Work email address")
    password: str = Field(..., min_length=8, max_length=128, description="Account password (min 8 characters)")
    full_name: str = Field(..., min_length=2, max_length=128, description="Full legal name")
    company_name: str = Field(..., min_length=2, max_length=128, description="Workspace or company name")


class LoginRequest(BaseModel):
    """Payload for email and password authentication."""

    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")


class UserResponse(BaseModel):
    """User profile response with company metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    company_id: uuid.UUID | None = None
    company: CompanyResponse | None = None
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    """JWT bearer token and authenticated user payload."""

    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int = 60
    user: UserResponse


class TokenPayload(BaseModel):
    """Decoded JWT payload structure."""

    sub: str  # user_id
    email: str
    company_id: str | None = None
    role: str
    exp: int


class SwitchCompanyRequest(BaseModel):
    """Request to switch active company context."""

    company_id: uuid.UUID


class ForgotPasswordRequest(BaseModel):
    """Payload to initiate password reset."""

    email: EmailStr = Field(..., description="Account email address")


class ResetPasswordRequest(BaseModel):
    """Payload to complete password reset."""

    email: EmailStr = Field(..., description="Account email address")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password (min 8 characters)")

