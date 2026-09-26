"""
AI Call Analytics — Authentication Dependencies & Security Guards.

Provides FastAPI dependencies for extracting authenticated users, enforcing active status,
verifying role-based access, and retrieving the active tenant context.
"""

from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.core.exceptions import AuthenticationError, ForbiddenError
from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.repositories.user_repository import UserRepository
from backend.app.services.auth_service import AuthService

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> User:
    """
    Extract, validate JWT bearer token (from Authorization header or ?token query param),
    and return the active User record.
    Raises AuthenticationError if token is absent, invalid, or expired.
    """
    raw_token = credentials.credentials if credentials else token
    if not raw_token:
        raise AuthenticationError("Authentication token is required.")

    payload = AuthService.decode_access_token(raw_token)
    if not payload:
        raise AuthenticationError("Invalid or expired authentication token.")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AuthenticationError("Malformed token: missing subject identifier.")

    try:
        user_id = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise AuthenticationError("Malformed token: subject is not a valid UUID.")

    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise AuthenticationError("User account does not exist.")

    if not user.is_active:
        raise AuthenticationError("User account is inactive.")

    # If user belongs to a company, ensure the company is active
    if user.company_id is not None and user.company is not None and not user.company.is_active:
        raise ForbiddenError("Company workspace is deactivated. Please contact platform administrator.")

    return user


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    """
    Optionally extract authenticated user. Returns None if unauthenticated.
    """
    raw_token = credentials.credentials if credentials else token
    if not raw_token:
        return None

    payload = AuthService.decode_access_token(raw_token)
    if not payload:
        return None

    user_id_str = payload.get("sub")
    if not user_id_str:
        return None

    try:
        user_id = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        return None

    user = UserRepository.get_by_id(db, user_id)
    if not user or not user.is_active:
        return None

    if user.company_id is not None and user.company is not None and not user.company.is_active:
        return None

    return user


require_authenticated_user = get_current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency enforcing that current user has ADMIN role."""
    from backend.app.models.user import UserRole
    if current_user.role != UserRole.ADMIN.value:
        raise ForbiddenError("Administrative privileges required.")
    return current_user


def require_company(current_user: User = Depends(get_current_user)) -> User:
    """Dependency enforcing that current user has COMPANY role."""
    from backend.app.models.user import UserRole
    if current_user.role != UserRole.COMPANY.value or not current_user.company_id:
        raise ForbiddenError("Company customer account required.")
    return current_user


def require_company_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency allowing access to either COMPANY or ADMIN role."""
    from backend.app.models.user import UserRole
    if current_user.role not in (UserRole.ADMIN.value, UserRole.COMPANY.value):
        raise ForbiddenError("Authorized role required.")
    return current_user


def require_role(*allowed_roles: str) -> Callable[[User], User]:
    """
    Dependency factory ensuring the current user possesses one of the specified roles.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenError(
                f"Role '{current_user.role}' is not authorized. Required: {', '.join(allowed_roles)}."
            )
        return current_user

    return role_checker


def get_current_company_id(
    current_user: User = Depends(get_current_user),
) -> uuid.UUID | None:
    """Convenience dependency returning the active company UUID for the current request."""
    return current_user.company_id

