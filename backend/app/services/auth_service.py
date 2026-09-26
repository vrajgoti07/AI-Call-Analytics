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
            "company_id": str(user.company_id) if user.company_id else None,
            "role": user.role,
        }
        return cls.create_access_token(claims)

    @classmethod
    def register(cls, db: Session, req: RegisterRequest) -> tuple[User, str]:
        """
        Register a new workspace and customer account.
        Always sets role=COMPANY and associates the user with the newly created company.
        Ensures atomic transaction: if user creation fails, company creation is rolled back.
        """
        existing_user = UserRepository.get_by_email(db, req.email)
        if existing_user is not None:
            raise ValueError(f"User with email '{req.email}' already exists.")

        try:
            # Check or create company
            company = CompanyRepository.get_by_name(db, req.company_name)
            if company is None:
                company = CompanyRepository.create(db, req.company_name)
            elif not company.is_active:
                raise ValueError(f"Company '{req.company_name}' is currently inactive.")

            hashed_pw = cls.hash_password(req.password)
            user = UserRepository.create(
                db=db,
                email=req.email,
                hashed_password=hashed_pw,
                full_name=req.full_name,
                company_id=company.id,
                role=UserRole.COMPANY.value,
            )

            db.commit()
            db.refresh(user)
            db.refresh(company)

            token = cls.generate_token_for_user(user)
            return user, token
        except Exception:
            db.rollback()
            raise

    @classmethod
    def authenticate(cls, db: Session, email: str, password: str) -> User | None:
        """Authenticate user by email and password, checking user and company active status."""
        user = UserRepository.get_by_email(db, email)
        if user is None:
            return None
        if not user.is_active:
            return None
        if not cls.verify_password(password, user.hashed_password):
            return None
        # Check company active status if user belongs to a company
        if user.company_id is not None and user.company is not None and not user.company.is_active:
            raise ValueError("Company workspace is disabled. Please contact platform administrator.")
        return user

    @classmethod
    def forgot_password(cls, db: Session, email: str) -> dict[str, str]:
        """Initiate password reset flow for registered user."""
        user = UserRepository.get_by_email(db, email)
        if not user or not user.is_active:
            # Return same friendly message to prevent email enumeration
            return {
                "message": "If your email is registered, you will receive password reset instructions.",
                "status": "ok",
            }

        # Generate a password reset token (valid for 15 minutes)
        reset_token = cls.create_access_token(
            {"sub": str(user.id), "email": user.email, "type": "password_reset"},
            expires_delta=timedelta(minutes=15),
        )
        return {
            "message": "If your email is registered, you will receive password reset instructions.",
            "status": "ok",
            "reset_token": reset_token,
        }

    @classmethod
    def reset_password(cls, db: Session, email: str, new_password: str) -> User:
        """Reset user password."""
        user = UserRepository.get_by_email(db, email)
        if not user:
            raise ValueError(f"No account found with email '{email}'.")
        if not user.is_active:
            raise ValueError("User account is disabled.")

        user.hashed_password = cls.hash_password(new_password)
        db.commit()
        db.refresh(user)
        return user
