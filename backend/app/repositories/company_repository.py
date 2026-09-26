"""
AI Call Analytics — Company Repository.
"""

from __future__ import annotations

import re
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.company import Company


def slugify(text: str) -> str:
    """Generate a clean URL-friendly slug from a company name."""
    clean = re.sub(r"[^\w\s-]", "", text.strip().lower())
    slug = re.sub(r"[\s_-]+", "-", clean).strip("-")
    return slug or "workspace"


class CompanyRepository:
    """Repository handling CRUD operations for Company tenant entities."""

    @staticmethod
    def get_by_id(db: Session, company_id: uuid.UUID) -> Company | None:
        """Fetch company by ID."""
        stmt = select(Company).where(Company.id == company_id)
        return db.scalar(stmt)

    @staticmethod
    def get_by_name(db: Session, name: str) -> Company | None:
        """Fetch company by exact name (case-insensitive)."""
        stmt = select(Company).where(Company.name.ilike(name.strip()))
        return db.scalar(stmt)

    @staticmethod
    def get_by_slug(db: Session, slug: str) -> Company | None:
        """Fetch company by slug."""
        stmt = select(Company).where(Company.slug == slug.strip().lower())
        return db.scalar(stmt)

    @staticmethod
    def create(db: Session, name: str, slug: str | None = None) -> Company:
        """
        Create a new company. If slug is not provided, generate one uniquely.
        """
        clean_name = name.strip()
        base_slug = slug or slugify(clean_name)
        unique_slug = base_slug

        counter = 1
        while CompanyRepository.get_by_slug(db, unique_slug) is not None:
            unique_slug = f"{base_slug}-{counter}"
            counter += 1

        company = Company(
            id=uuid.uuid4(),
            name=clean_name,
            slug=unique_slug,
            is_active=True,
        )
        db.add(company)
        db.flush()
        return company

    @staticmethod
    def list_all(db: Session) -> list[Company]:
        """Fetch all companies ordered by creation date."""
        stmt = select(Company).where(Company.is_active.is_(True)).order_by(Company.created_at)
        return list(db.scalars(stmt).all())
