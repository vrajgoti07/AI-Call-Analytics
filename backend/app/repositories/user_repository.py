"""
AI Call Analytics — User Repository.
"""

from __future__ import annotations

import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.app.models.user import User, UserRole


class UserRepository:
    """Repository handling CRUD operations for User entities."""

    @staticmethod
    def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
        """Fetch user by primary key with company relationship eagerly loaded."""
        stmt = (
            select(User)
            .options(joinedload(User.company))
            .where(User.id == user_id)
        )
        return db.scalar(stmt)

    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        """Fetch user by unique email with company eagerly loaded."""
        stmt = (
            select(User)
            .options(joinedload(User.company))
            .where(User.email == email.strip().lower())
        )
        return db.scalar(stmt)

    @staticmethod
    def create(
        db: Session,
        email: str,
        hashed_password: str,
        full_name: str,
        company_id: uuid.UUID,
        role: str = UserRole.ANALYST.value,
    ) -> User:
        """Create and persist a new user record."""
        user = User(
            id=uuid.uuid4(),
            email=email.strip().lower(),
            hashed_password=hashed_password,
            full_name=full_name.strip(),
            company_id=company_id,
            role=role,
            is_active=True,
        )
        db.add(user)
        db.flush()
        return user

    @staticmethod
    def list_by_company(db: Session, company_id: uuid.UUID) -> list[User]:
        """List all active users belonging to a company."""
        stmt = (
            select(User)
            .where(User.company_id == company_id, User.is_active.is_(True))
            .order_by(User.created_at)
        )
        return list(db.scalars(stmt).all())
