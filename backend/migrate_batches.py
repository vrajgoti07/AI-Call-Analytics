"""
AI Call Analytics — Database Migration for Ingestion Batches.

Creates ingestion_batches table, adds batch_id FK to calls and reports,
and associates existing calls with a default legacy batch if unassigned.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure paths
_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent
for _p in [str(_PROJECT_ROOT), str(_BACKEND_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from sqlalchemy import text
from backend.app.database.session import sync_engine, SyncSessionLocal
from backend.app.models.base import Base
from backend.app.models.ingestion_batch import IngestionBatch, BatchStatus, BatchUploadType
from backend.app.models.call import Call
from backend.app.models.report import Report
from backend.app.models.company import Company


def run_migration():
    print("Beginning Ingestion Batches database migration...")

    # 1. Create ingestion_batches table if not exists
    Base.metadata.create_all(bind=sync_engine, tables=[IngestionBatch.__table__])
    print("Verified/created 'ingestion_batches' table.")

    # 2. Add batch_id column to calls and reports
    with sync_engine.connect() as conn:
        # Check calls.batch_id
        check_col_sql = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='calls' AND column_name='batch_id';
        """)
        res = conn.execute(check_col_sql).scalar()
        if not res:
            print("Adding 'batch_id' column and index to 'calls' table...")
            conn.execute(text("""
                ALTER TABLE calls 
                ADD COLUMN batch_id UUID REFERENCES ingestion_batches(id) ON DELETE SET NULL;
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_calls_company_batch ON calls (company_id, batch_id);
                CREATE INDEX IF NOT EXISTS ix_calls_batch_id ON calls (batch_id);
            """))
            conn.commit()
            print("Added 'batch_id' column to 'calls' table.")
        else:
            print("'batch_id' column already exists on 'calls' table.")

        # Check reports.batch_id
        check_col_sql = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='reports' AND column_name='batch_id';
        """)
        res = conn.execute(check_col_sql).scalar()
        if not res:
            print("Adding 'batch_id' column and index to 'reports' table...")
            conn.execute(text("""
                ALTER TABLE reports 
                ADD COLUMN batch_id UUID REFERENCES ingestion_batches(id) ON DELETE SET NULL;
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_reports_company_batch ON reports (company_id, batch_id);
                CREATE INDEX IF NOT EXISTS ix_reports_batch_id ON reports (batch_id);
            """))
            conn.commit()
            print("Added 'batch_id' column to 'reports' table.")
        else:
            print("'batch_id' column already exists on 'reports' table.")

    # 3. Associate existing orphan calls with a legacy batch per company
    with SyncSessionLocal() as session:
        companies = session.query(Company).all()
        for comp in companies:
            orphan_calls = session.query(Call).filter(
                Call.company_id == comp.id,
                Call.batch_id.is_(None),
            ).all()

            if orphan_calls:
                batch_id = uuid.uuid4()
                batch_name = "Initial Batch (Pre-existing Calls)"
                legacy_batch = IngestionBatch(
                    id=batch_id,
                    company_id=comp.id,
                    original_filename="initial_archive.zip",
                    display_name=batch_name,
                    upload_type=BatchUploadType.ZIP.value,
                    status=BatchStatus.COMPLETED.value,
                    total_files=len(orphan_calls),
                    processed_count=len(orphan_calls),
                    skipped_count=0,
                    failed_count=0,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                )
                session.add(legacy_batch)
                session.flush()

                for call in orphan_calls:
                    call.batch_id = legacy_batch.id

                session.commit()
                print(f"Grouped {len(orphan_calls)} legacy calls for company '{comp.name}' into batch '{legacy_batch.display_name}'.")
            else:
                print(f"No unassigned calls for company '{comp.name}'.")

    print("Ingestion Batches migration completed successfully!")


if __name__ == "__main__":
    run_migration()
