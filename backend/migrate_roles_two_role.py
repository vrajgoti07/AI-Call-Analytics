"""
Database Migration: Exactly Two Roles (ADMIN, COMPANY), Nullable company_id for ADMIN,
and Bootstrap Admin Account vrajgoti07@gmail.com.
"""

import sys
import uuid
from sqlalchemy import text

sys.path.insert(0, ".")
sys.path.insert(0, "..")

from backend.app.database.session import sync_engine, SyncSessionLocal
from backend.app.models.user import User
from backend.app.models.company import Company
from backend.app.services.auth_service import AuthService


def migrate_roles():
    print("Beginning two-role migration...")

    # 1. Make company_id nullable on users table if not already nullable
    with sync_engine.connect() as conn:
        print("Ensuring users.company_id is nullable for system ADMIN...")
        conn.execute(text("ALTER TABLE users ALTER COLUMN company_id DROP NOT NULL;"))
        conn.commit()
        print("users.company_id is now nullable.")

    # 2. Update existing user roles in database
    with SyncSessionLocal() as session:
        # Update existing company users to COMPANY
        updated_count = session.execute(
            text("UPDATE users SET role = 'COMPANY' WHERE role IN ('analyst', 'viewer', 'user', 'manager', 'admin');")
        ).rowcount
        session.commit()
        print(f"Updated {updated_count} existing users to 'COMPANY'.")

        # 3. Create or update requested ADMIN account
        admin_email = "vrajgoti07@gmail.com"
        admin_pw = "123456789"
        admin = session.query(User).filter(User.email == admin_email).first()

        hashed_pw = AuthService.hash_password(admin_pw)
        if not admin:
            admin = User(
                id=uuid.uuid4(),
                email=admin_email,
                hashed_password=hashed_pw,
                full_name="Platform Admin",
                role="ADMIN",
                company_id=None,
                is_active=True,
            )
            session.add(admin)
            print(f"Created ADMIN user: {admin_email}")
        else:
            admin.role = "ADMIN"
            admin.hashed_password = hashed_pw
            admin.is_active = True
            admin.company_id = None
            print(f"Updated existing user {admin_email} to ADMIN.")

        session.commit()
        print("Role migration and admin bootstrap complete.")


if __name__ == "__main__":
    migrate_roles()
