"""
AI Call Analytics — Authentication Service.

Handles password hashing via direct bcrypt, JWT token lifecycle via python-jose,
and tenant-aware user registration and authentication.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.user import User, UserRole
from backend.app.repositories.company_repository import CompanyRepository
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.auth import RegisterRequest


class AuthService:
    """Service encapsulating authentication, password hashing, and token issuance."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plaintext password with bcrypt (capped at 72 bytes)."""
        pw_bytes = password.encode("utf-8")[:72]
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against a stored bcrypt hash."""
        try:
            pw_bytes = plain_password.encode("utf-8")[:72]
            return bcrypt.checkpw(pw_bytes, hashed_password.encode("utf-8"))
        except Exception:
            return False

    @staticmethod
    def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
        """Create a signed JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiration_minutes)

        to_encode.update({"exp": int(expire.timestamp())})
        return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    @staticmethod
    def decode_access_token(token: str) -> dict[str, Any] | None:
        """Decode and validate a JWT access token."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
            return payload
        except JWTError:
            return None

    @classmethod
    def generate_token_for_user(cls, user: User) -> str:
        """Generate JWT token containing user identity and company context."""
        claims = {
            "sub": str(user.id),
            "email": user.email,
            "company_id": str(user.company_id),
            "role": user.role,
        }
        return cls.create_access_token(claims)

    @classmethod
    def register(cls, db: Session, req: RegisterRequest) -> tuple[User, str]:
        """
        Register a new workspace and tenant admin user.
        If the company already exists, joins it as analyst; if newly created, sets as admin.
        """
        existing_user = UserRepository.get_by_email(db, req.email)
        if existing_user is not None:
            raise ValueError(f"User with email '{req.email}' already exists.")

        company = CompanyRepository.get_by_name(db, req.company_name)
        role = UserRole.ANALYST.value

        if company is None:
            company = CompanyRepository.create(db, req.company_name)
            role = UserRole.ADMIN.value
        else:
            # If company already exists, check if any users exist in this company
            users_in_company = UserRepository.list_by_company(db, company.id)
            if not users_in_company:
                role = UserRole.ADMIN.value

        hashed_pw = cls.hash_password(req.password)
        user = UserRepository.create(
            db=db,
            email=req.email,
            hashed_password=hashed_pw,
            full_name=req.full_name,
            company_id=company.id,
            role=role,
        )

        db.commit()
        db.refresh(user)
        db.refresh(company)

        token = cls.generate_token_for_user(user)
        return user, token

    @classmethod
    def authenticate(cls, db: Session, email: str, password: str) -> User | None:
        """Authenticate user by email and password."""
        user = UserRepository.get_by_email(db, email)
        if user is None:
            return None
        if not user.is_active:
            return None
        if not cls.verify_password(password, user.hashed_password):
            return None
        return user
