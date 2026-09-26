"""
AI Call Analytics — Authentication & Workspace Management API Router.
"""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.core.auth import get_current_user
from backend.app.core.exceptions import (
    AppException,
    AuthenticationError,
    CompanyNotFoundError,
    ForbiddenError,
)
from backend.app.database.session import get_db
from backend.app.models.user import User, UserRole
from backend.app.repositories.company_repository import CompanyRepository
from backend.app.schemas.auth import (
    CompanyCreate,
    CompanyResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SwitchCompanyRequest,
    TokenResponse,
    UserResponse,
)
from backend.app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new company customer account",
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Register a new company workspace and customer account.
    Always creates a user with role=COMPANY and associates it with the new company.
    """
    try:
        user, token = AuthService.register(db=db, req=payload)
    except ValueError as err:
        raise AppException(
            code="REGISTRATION_FAILED",
            message=str(err),
            status_code=status.HTTP_409_CONFLICT,
        )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and obtain JWT token",
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate against existing user credentials (supports both ADMIN and COMPANY).
    Returns a signed JWT bearer token on success.
    """
    try:
        user = AuthService.authenticate(db=db, email=payload.email, password=payload.password)
    except ValueError as err:
        raise ForbiddenError(str(err))

    if not user:
        raise AuthenticationError("Invalid email or password.")

    token = AuthService.generate_token_for_user(user)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/forgot-password",
    summary="Request a password reset link/token",
)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Request password reset. Returns standard confirmation message."""
    return AuthService.forgot_password(db=db, email=payload.email)


@router.post(
    "/reset-password",
    summary="Reset account password",
)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Reset password for a registered account."""
    try:
        AuthService.reset_password(db=db, email=payload.email, new_password=payload.new_password)
        return {"message": "Password reset successfully. You can now log in.", "status": "ok"}
    except ValueError as err:
        raise AppException(
            code="RESET_FAILED",
            message=str(err),
            status_code=status.HTTP_400_BAD_REQUEST,
        )



@router.get(
    "/me",
    response_model=UserResponse,
    summary="Retrieve profile and active company for current user",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the profile information and company association for the authenticated session."""
    return UserResponse.model_validate(current_user)


@router.get(
    "/companies",
    response_model=list[CompanyResponse],
    summary="List available company workspaces",
)
def list_companies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CompanyResponse]:
    """
    Retrieve workspaces. Admins can see all workspaces, companies see their active company.
    """
    if current_user.role == UserRole.ADMIN.value:
        companies = CompanyRepository.list_all(db)
    else:
        company = CompanyRepository.get_by_id(db, current_user.company_id)
        companies = [company] if company else []

    return [CompanyResponse.model_validate(c) for c in companies]


@router.post(
    "/switch-company",
    response_model=TokenResponse,
    summary="Switch active workspace context",
)
def switch_company(
    payload: SwitchCompanyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Switch active company for administrators and re-issue a JWT token with updated tenant claims.
    """
    company = CompanyRepository.get_by_id(db, payload.company_id)
    if not company or not company.is_active:
        raise CompanyNotFoundError(payload.company_id)

    if current_user.role != UserRole.ADMIN.value:
        raise ForbiddenError("Company accounts cannot switch workspaces.")

    current_user.company_id = payload.company_id
    db.commit()
    db.refresh(current_user)

    new_token = AuthService.generate_token_for_user(current_user)
    return TokenResponse(
        access_token=new_token,
        token_type="bearer",
        user=UserResponse.model_validate(current_user),
    )


@router.post(
    "/logout",
    summary="Log out and invalidate session",
)
def logout(
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Logout authenticated user session."""
    return {"message": "Logged out successfully", "status": "ok"}


@router.post(
    "/companies",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new company workspace (Admin only)",
)
def create_company(
    payload: CompanyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompanyResponse:
    """Create a new workspace. Only administrators can create new workspaces."""
    if current_user.role != UserRole.ADMIN.value:
        raise ForbiddenError("Only workspace administrators can create new companies.")

    existing = CompanyRepository.get_by_name(db, payload.name)
    if existing:
        raise AppException(
            code="COMPANY_EXISTS",
            message=f"Company with name '{payload.name}' already exists.",
            status_code=status.HTTP_409_CONFLICT,
        )

    company = CompanyRepository.create(db=db, name=payload.name)
    db.commit()
    db.refresh(company)
    return CompanyResponse.model_validate(company)
