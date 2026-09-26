"""
AI Call Analytics — Database Migration for Companies, Users, and Multi-Tenancy.

Creates companies and users tables, adds company_id FK to calls, and seeds default tenant.
"""

import sys
import uuid

# Ensure parent directory is in python path
sys.path.insert(0, ".")
sys.path.insert(0, "..")

from sqlalchemy import text
from backend.app.database.session import sync_engine, SyncSessionLocal
from backend.app.models.base import Base
from backend.app.models.company import Company
from backend.app.models.user import User, UserRole
from backend.app.models.call import Call
from backend.app.services.auth_service import AuthService


def run_migration():
    print("Beginning multi-tenant database migration...")

    # 1. Create tables defined in models if not exist
    Base.metadata.create_all(bind=sync_engine, tables=[Company.__table__, User.__table__])
    print("Verified/created 'companies' and 'users' tables.")

    # 2. Add company_id column to calls table if it does not exist
    with sync_engine.connect() as conn:
        # Check if column exists
        check_col_sql = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='calls' AND column_name='company_id';
        """)
        res = conn.execute(check_col_sql).scalar()
        if not res:
            print("Adding 'company_id' column and index to 'calls' table...")
            conn.execute(text("""
                ALTER TABLE calls 
                ADD COLUMN company_id UUID REFERENCES companies(id) ON DELETE SET NULL;
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_calls_company_created_at ON calls (company_id, created_at);
                CREATE INDEX IF NOT EXISTS ix_calls_company_status ON calls (company_id, status);
            """))
            conn.commit()
            print("Added 'company_id' column and indexes successfully.")
        else:
            print("'company_id' column already exists on 'calls' table.")

    # 3. Seed default workspace and admin user, backfill existing calls
    with SyncSessionLocal() as session:
        # Check or create default company
        default_company = session.query(Company).filter(Company.slug == "acme-corp").first()
        if not default_company:
            default_company = Company(
                id=uuid.uuid4(),
                name="Acme Corp",
                slug="acme-corp",
                is_active=True,
            )
            session.add(default_company)
            session.flush()
            print(f"Created default company: {default_company.name} ({default_company.id})")
        else:
            print(f"Found existing default company: {default_company.name} ({default_company.id})")

        # Check or create default admin user
        admin_email = "admin@acmecorp.com"
        admin_user = session.query(User).filter(User.email == admin_email).first()
        if not admin_user:
            hashed_pw = AuthService.hash_password("Password123!")
            admin_user = User(
                id=uuid.uuid4(),
                email=admin_email,
                hashed_password=hashed_pw,
                full_name="System Administrator",
                role=UserRole.ADMIN.value,
                company_id=default_company.id,
                is_active=True,
            )
            session.add(admin_user)
            session.flush()
            print(f"Created default admin user: {admin_email} (Password: Password123!)")
        else:
            print(f"Admin user already exists: {admin_email}")

        # 4. Associate existing orphan calls with default company
        orphan_calls = session.query(Call).filter(Call.company_id.is_(None)).all()
        if orphan_calls:
            print(f"Assigning {len(orphan_calls)} existing calls to company '{default_company.name}'...")
            for call in orphan_calls:
                call.company_id = default_company.id
            session.commit()
            print("Successfully associated existing calls.")
        else:
            session.commit()
            print("All calls already belong to a company.")

    print("Multi-tenant migration completed successfully!")


if __name__ == "__main__":
    run_migration()
