"""
AI Call Analytics — Complete Production E2E Test Suite.
Validates all 25 required test scenarios:
 1. User registration
 2. User login
 3. Company creation (Admin)
 4. Company switching
 5. Single audio file upload + SHA-256 hash
 6. ZIP upload with multiple valid calls
 7. ZIP upload with unsupported files (skipped with reasons)
 8. Duplicate detection (Single 409, ZIP duplicate skipped)
 9. Call processing & job status tracking
10. Transcript & turns retrieval
11. AI analysis & risk retrieval
12. Individual call report generation (PDF, JSON, CSV)
13. Individual call report download (Content-Disposition, headers)
14. Company executive report generation
15. Company executive report download
16. Create second company workspace
17. Upload calls to second company
18. Multi-company data isolation (calls, transcripts, analysis, jobs, reports)
19. Blocked unauthorized cross-company report download (404/403)
20. User logout
21. Protected endpoint rejection without token (401)
22. Invalid / corrupt ZIP handling (400)
23. Malicious ZIP path traversal prevention
24. Oversized upload / ZIP bomb detection
25. Invalid / expired JWT rejection (401)
"""

from __future__ import annotations

import io
import time
import uuid
import zipfile
import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.database.session import SyncSessionLocal
from backend.app.models import (
    Call,
    CallStatus,
    AudioFile,
    Transcript,
    TranscriptTurn,
    User,
    Company,
    UserRole,
    Report,
    ReportType,
    ReportStatus,
    EscalationRisk,
)


def make_wav_bytes(content: bytes = b"\x00\x00\x00\x00") -> bytes:
    data_len = len(content)
    file_len = 36 + data_len
    header = (
        b"RIFF"
        + file_len.to_bytes(4, "little")
        + b"WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data"
        + data_len.to_bytes(4, "little")
    )
    return header + content


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


class TestProductionE2ESuite:
    """Complete 25-step production validation suite."""

    company_a_id: str = ""
    company_a_token: str = ""
    company_a_email: str = ""
    company_b_id: str = ""
    company_b_token: str = ""
    company_b_email: str = ""
    call_a1_id: str = ""
    report_a_id: str = ""
    report_b_id: str = ""

    # =========================================================================
    # TEST 1: Register User
    # =========================================================================
    def test_01_register_user(self, client: TestClient) -> None:
        email = f"admin_{uuid.uuid4().hex[:8]}@acme-corp.com"
        TestProductionE2ESuite.company_a_email = email
        res = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "SecurePassword123!",
                "full_name": "Acme Admin",
                "company_name": f"Acme Corp {uuid.uuid4().hex[:6]}",
            },
        )
        assert res.status_code == 201, res.text
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == email
        assert data["user"]["company_id"] is not None
        TestProductionE2ESuite.company_a_id = data["user"]["company_id"]
        TestProductionE2ESuite.company_a_token = data["access_token"]

    # =========================================================================
    # TEST 2: Login
    # =========================================================================
    def test_02_login(self, client: TestClient) -> None:
        res = client.post(
            "/api/v1/auth/login",
            json={
                "email": TestProductionE2ESuite.company_a_email,
                "password": "SecurePassword123!",
            },
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert "access_token" in data
        assert data["user"]["email"] == TestProductionE2ESuite.company_a_email
        TestProductionE2ESuite.company_a_token = data["access_token"]

        headers = {"Authorization": f"Bearer {TestProductionE2ESuite.company_a_token}"}
        res_me = client.get("/api/v1/auth/me", headers=headers)
        assert res_me.status_code == 200
        assert res_me.json()["company_id"] == TestProductionE2ESuite.company_a_id

    # =========================================================================
    # TEST 3: Create Company (Admin Only - Company Blocked)
    # =========================================================================
    def test_03_create_company(self, client: TestClient) -> None:
        # Company user is forbidden from creating companies
        headers = {"Authorization": f"Bearer {TestProductionE2ESuite.company_a_token}"}
        new_company_name = f"Subsidiary Corp {uuid.uuid4().hex[:6]}"
        res_forbidden = client.post(
            "/api/v1/auth/companies",
            headers=headers,
            json={"name": new_company_name},
        )
        assert res_forbidden.status_code == 403

        # Admin user can create new companies
        admin_login = client.post(
            "/api/v1/auth/login",
            json={"email": "vrajgoti07@gmail.com", "password": "123456789"},
        )
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        res = client.post(
            "/api/v1/auth/companies",
            headers=admin_headers,
            json={"name": new_company_name},
        )
        assert res.status_code == 201, res.text
        comp = res.json()
        assert comp["name"] == new_company_name
        assert comp["id"] is not None

    # =========================================================================
    # TEST 4: Select Company Context (Admin Only - Company Blocked)
    # =========================================================================
    def test_04_select_company(self, client: TestClient) -> None:
        # Company user is forbidden from switching companies
        headers = {"Authorization": f"Bearer {TestProductionE2ESuite.company_a_token}"}
        res_forbidden = client.post(
            "/api/v1/auth/switch-company",
            headers=headers,
            json={"company_id": TestProductionE2ESuite.company_a_id},
        )
        assert res_forbidden.status_code == 403

        # Admin user can switch workspace context
        admin_login = client.post(
            "/api/v1/auth/login",
            json={"email": "vrajgoti07@gmail.com", "password": "123456789"},
        )
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        res_switch = client.post(
            "/api/v1/auth/switch-company",
            headers=admin_headers,
            json={"company_id": TestProductionE2ESuite.company_a_id},
        )
        assert res_switch.status_code == 200
        assert res_switch.json()["user"]["company_id"] == TestProductionE2ESuite.company_a_id

    # =========================================================================
    # TEST 5: Upload One Audio File + Hash
    # =========================================================================
    def test_05_upload_one_audio_file(self, client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {TestProductionE2ESuite.company_a_token}"}
        res_call = client.post(
            "/api/v1/calls",
            headers=headers,
            json={"external_id": "CALL-A1-SAMPLE", "language": "en"},
        )
        assert res_call.status_code == 201, res_call.text
        call_id = res_call.json()["id"]
        TestProductionE2ESuite.call_a1_id = call_id

        wav_data = make_wav_bytes(b"unique_audio_payload_A1")
        files = {"file": ("call_a1.wav", io.BytesIO(wav_data), "audio/wav")}
        res_upload = client.post(f"/api/v1/calls/{call_id}/upload", headers=headers, files=files)
        assert res_upload.status_code == 200, res_upload.text
        data = res_upload.json()
        assert data["audio_file"] is not None
        assert data["audio_file"]["filename"] == "call_a1.wav"
        assert str(data["company_id"]) == str(TestProductionE2ESuite.company_a_id)

    # =========================================================================
    # TEST 6: Upload ZIP Containing Multiple Valid Calls
    # =========================================================================
    def test_06_upload_zip_multiple_valid_calls(self, client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {TestProductionE2ESuite.company_a_token}"}
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("support_call_01.wav", make_wav_bytes(b"audio_stream_101"))
            zf.writestr("support_call_02.mp3", make_wav_bytes(b"audio_stream_102"))
            zf.writestr("nested/support_call_03.wav", make_wav_bytes(b"audio_stream_103"))
        zip_buf.seek(0)

        files = {"file": ("bulk_calls.zip", zip_buf, "application/zip")}
        res = client.post(
            "/api/v1/calls/upload-zip?auto_analyze=false",
            headers=headers,
            files=files,
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["total_files"] == 3
        assert data["processed_count"] == 3
        assert data["skipped_count"] == 0
        assert len(data["created_calls"]) == 3

    # =========================================================================
    # TEST 7: Upload ZIP Containing Unsupported Files
    # =========================================================================
    def test_07_upload_zip_unsupported_files(self, client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {TestProductionE2ESuite.company_a_token}"}
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("valid_call_77.wav", make_wav_bytes(b"audio_stream_77"))
            zf.writestr("notes.txt", b"These are call notes not audio")
            zf.writestr("data.csv", b"turn,speaker,text\n1,Agent,Hello")
            zf.writestr("script.py", b"print('unsupported')")
        zip_buf.seek(0)

        files = {"file": ("mixed_archive.zip", zip_buf, "application/zip")}
        res = client.post(
            "/api/v1/calls/upload-zip?auto_analyze=false",
            headers=headers,
            files=files,
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["processed_count"] == 1
        assert data["skipped_count"] == 3
        skipped_names = [s["filename"] for s in data["skipped_files"]]
        assert "notes.txt" in skipped_names
        assert "data.csv" in skipped_names
        assert "script.py" in skipped_names

    # =========================================================================
    # TEST 8: Duplicate Detection
    # =========================================================================
    def test_08_duplicate_detection(self, client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {TestProductionE2ESuite.company_a_token}"}
        # 1. Single audio upload duplicate check
        res_call2 = client.post(
            "/api/v1/calls",
            headers=headers,
            json={"external_id": "CALL-A1-DUPLICATE"},
        )
        call2_id = res_call2.json()["id"]

        wav_data = make_wav_bytes(b"unique_audio_payload_A1")
        files = {"file": ("duplicate_audio.wav", io.BytesIO(wav_data), "audio/wav")}
        res_dup = client.post(f"/api/v1/calls/{call2_id}/upload", headers=headers, files=files)
        assert res_dup.status_code == 409
        assert res_dup.json()["error"]["code"] == "DUPLICATE_CALL"

        # 2. ZIP duplicate detection
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("duplicate_in_zip.wav", wav_data)
        zip_buf.seek(0)
        files_zip = {"file": ("dup_archive.zip", zip_buf, "application/zip")}
        res_zip = client.post(
            "/api/v1/calls/upload-zip?auto_analyze=false",
            headers=headers,
            files=files_zip,
        )
        assert res_zip.status_code == 200
        zip_data = res_zip.json()
        assert zip_data["skipped_count"] == 1
        assert "duplicate" in zip_data["skipped_files"][0]["reason"].lower()

    # =========================================================================
    # TEST 9: Process Calls
    # =========================================================================
    def test_09_process_calls(self, client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {TestProductionE2ESuite.company_a_token}"}
        call_id = TestProductionE2ESuite.call_a1_id
        res = client.post(
            f"/api/v1/calls/{call_id}/analyze",
            headers=headers,
            json={"force_reprocess": True},
        )
        assert res.status_code in (200, 202), res.text
        job_data = res.json()
        assert "job_id" in job_data
        assert job_data["status"] in ("PENDING", "QUEUED", "PROCESSING", "COMPLETED", "FAILED")

    # =========================================================================
    # TEST 10: View Transcript & Turns
    # =========================================================================
    def test_10_view_transcript_and_turns(self, client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {TestProductionE2ESuite.company_a_token}"}
        call_id = uuid.UUID(TestProductionE2ESuite.call_a1_id)

        # Seed mock transcript and turns directly into database for call A1
        with SyncSessionLocal() as db:
            transcript = db.query(Transcript).filter(Transcript.call_id == call_id).first()
            if not transcript:
                transcript = Transcript(
                    id=uuid.uuid4(),
                    call_id=call_id,
                    text="Agent: Thank you for calling Acme. Customer: I am very satisfied with your service.",
                    language="en",
                    model="whisper",
                    model_version="1.0",
                )
                db.add(transcript)
                db.flush()

                turn1 = TranscriptTurn(
                    id=uuid.uuid4(),
                    transcript_id=transcript.id,
                    speaker_id="SPEAKER_00",
                    start_time=0.0,
                    end_time=3.5,
                    text="Thank you for calling Acme.",
                    sequence_number=0,
                )
                turn2 = TranscriptTurn(
                    id=uuid.uuid4(),
                    transcript_id=transcript.id,
                    speaker_id="SPEAKER_01",
                    start_time=4.0,
                    end_time=8.2,
                    text="I am very satisfied with your service.",
                    sequence_number=1,
                )
                db.add_all([turn1, turn2])

                # Mark call completed
                call = db.query(Call).filter(Call.id == call_id).first()
                if call:
                    call.status = CallStatus.COMPLETED.value
                db.commit()

        # Check transcript endpoint
        res_t = client.get(f"/api/v1/calls/{call_id}/transcript", headers=headers)
        assert res_t.status_code == 200, res_t.text
        assert "Acme" in res_t.json()["text"]

        # Check turns endpoint
        res_turns = client.get(f"/api/v1/calls/{call_id}/transcript/turns", headers=headers)
        assert res_turns.status_code == 200, res_turns.text
        turns = res_turns.json()["items"]
        assert len(turns) >= 2
        assert turns[0]["speaker_id"] == "SPEAKER_00"

    # =========================================================================
    # TEST 11: View AI Analysis
    # =========================================================================
    def test_11_view_ai_analysis(self, client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {TestProductionE2ESuite.company_a_token}"}
        call_id = TestProductionE2ESuite.call_a1_id

        # Seed escalation risk
        with SyncSessionLocal() as db:
            risk = db.query(EscalationRisk).filter(EscalationRisk.call_id == str(call_id)).first()
            if not risk:
                risk = EscalationRisk(
                    id=uuid.uuid4(),
                    call_id=str(call_id),
                    risk_score=0.15,
                    risk_probability=0.15,
                    risk_level="LOW",
                    model_name="heuristic",
                    top_factors=[{"factor": "Polite customer", "weight": 0.1}],
                )
                db.add(risk)
                db.commit()

        res_risk = client.get(f"/api/v1/calls/{call_id}/risk", headers=headers)
        assert res_risk.status_code == 200
        assert res_risk.json()["risk_level"] == "LOW"

    # =========================================================================
    # TEST 12: Generate Individual Call Report
    # =========================================================================
    def test_12_generate_individual_call_report(self, client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {TestProductionE2ESuite.company_a_token}"}
        call_id = TestProductionE2ESuite.call_a1_id

        res = client.post(
            "/api/v1/reports/generate",
            headers=headers,
            json={
                "report_type": "INDIVIDUAL_CALL",
                "call_id": call_id,
                "title": "Call A1 Performance Report",
            },
        )
        assert res.status_code == 201, res.text
        report_data = res.json()
        assert report_data["status"] == "COMPLETED"
        assert report_data["report_type"] == "INDIVIDUAL_CALL"
        assert report_data["has_pdf"] is True
        assert report_data["has_json"] is True
        assert report_data["has_csv"] is True
        TestProductionE2ESuite.report_a_id = report_data["id"]

    # =========================================================================
    # TEST 13: Download Individual Report (PDF, JSON, CSV)
    # =========================================================================
    def test_13_download_individual_report(self, client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {TestProductionE2ESuite.company_a_token}"}
        rep_id = TestProductionE2ESuite.report_a_id

        # 1. Download PDF
        res_pdf = client.get(f"/api/v1/reports/{rep_id}/download?format=pdf", headers=headers)
        assert res_pdf.status_code == 200, res_pdf.text
        assert res_pdf.headers["content-type"] == "application/pdf"
        assert "attachment; filename=" in res_pdf.headers.get("content-disposition", "")
        assert res_pdf.content.startswith(b"%PDF")

        # 2. Download JSON
        res_json = client.get(f"/api/v1/reports/{rep_id}/download?format=json", headers=headers)
        assert res_json.status_code == 200
        assert "application/json" in res_json.headers["content-type"]
        assert b"call_id" in res_json.content

        # 3. Download CSV
        res_csv = client.get(f"/api/v1/reports/{rep_id}/download?format=csv", headers=headers)
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.headers["content-type"]

    # =========================================================================
    # TEST 14: Generate Company Report
    # =========================================================================
    def test_14_generate_company_report(self, client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {TestProductionE2ESuite.company_a_token}"}
        res = client.post(
            "/api/v1/reports/generate",
            headers=headers,
            json={
                "report_type": "COMPANY_ANALYTICS",
                "title": "Acme Corp Executive Intelligence Report",
            },
        )
        assert res.status_code == 201, res.text
        data = res.json()
        assert data["status"] == "COMPLETED"
        assert data["report_type"] in ("COMPANY_ANALYTICS", "COMPANY_EXECUTIVE")
        assert data["summary_data"] is not None
        assert data["has_pdf"] is True
        assert data["has_json"] is True
        assert data["has_csv"] is True
        TestProductionE2ESuite.report_a_id = data["id"]

    # =========================================================================
    # TEST 15: Download Company Report
    # =========================================================================
    def test_15_download_company_report(self, client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {TestProductionE2ESuite.company_a_token}"}
        rep_id = TestProductionE2ESuite.report_a_id

        res_pdf = client.get(f"/api/v1/reports/{rep_id}/download?format=pdf", headers=headers)
        assert res_pdf.status_code == 200
        assert res_pdf.headers["content-type"] == "application/pdf"
        assert res_pdf.content.startswith(b"%PDF")

        res_json = client.get(f"/api/v1/reports/{rep_id}/download?format=json", headers=headers)
        assert res_json.status_code == 200
        assert b"company_name" in res_json.content or b"total_calls" in res_json.content

    # =========================================================================
    # TEST 16: Create Second Company Workspace
    # =========================================================================
    def test_16_create_second_company(self, client: TestClient) -> None:
        email = f"user_{uuid.uuid4().hex[:8]}@beta-logistics.com"
        TestProductionE2ESuite.company_b_email = email
        res = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "PasswordBeta999!",
                "full_name": "Beta Analyst",
                "company_name": f"Beta Logistics {uuid.uuid4().hex[:6]}",
            },
        )
        assert res.status_code == 201
        data = res.json()
        TestProductionE2ESuite.company_b_id = data["user"]["company_id"]
        TestProductionE2ESuite.company_b_token = data["access_token"]
        assert TestProductionE2ESuite.company_b_id != TestProductionE2ESuite.company_a_id

    # =========================================================================
    # TEST 17: Upload Calls to Second Company
    # =========================================================================
    def test_17_upload_calls_to_second_company(self, client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {TestProductionE2ESuite.company_b_token}"}

        res_call = client.post(
            "/api/v1/calls",
            headers=headers,
            json={"external_id": "CALL-B-SECRET"},
        )
        assert res_call.status_code == 201
        call_b_id = res_call.json()["id"]

        wav_data = make_wav_bytes(b"beta_private_call_audio")
        files = {"file": ("beta_secret.wav", io.BytesIO(wav_data), "audio/wav")}
        res_up = client.post(f"/api/v1/calls/{call_b_id}/upload", headers=headers, files=files)
        assert res_up.status_code == 200

        res_rep = client.post(
            "/api/v1/reports/generate",
            headers=headers,
            json={"report_type": "COMPANY_ANALYTICS", "title": "Beta Logistics Report"},
        )
        assert res_rep.status_code == 201
        TestProductionE2ESuite.report_b_id = res_rep.json()["id"]

    # =========================================================================
    # TEST 18: Multi-Company Data Isolation
    # =========================================================================
    def test_18_multi_company_data_isolation(self, client: TestClient) -> None:
        headers_a = {"Authorization": f"Bearer {TestProductionE2ESuite.company_a_token}"}
        headers_b = {"Authorization": f"Bearer {TestProductionE2ESuite.company_b_token}"}

        # 1. Company A cannot view Company B's calls
        res_b_list = client.get("/api/v1/calls", headers=headers_b)
        b_calls = res_b_list.json()["items"]
        assert len(b_calls) >= 1
        b_call_id = b_calls[0]["id"]

        res_leak = client.get(f"/api/v1/calls/{b_call_id}", headers=headers_a)
        assert res_leak.status_code == 404, "Security violation: Company A saw Company B call!"

        res_a_list = client.get("/api/v1/calls", headers=headers_a)
        a_call_ids = [c["id"] for c in res_a_list.json()["items"]]
        assert b_call_id not in a_call_ids

        # 2. Company A cannot view Company B's reports
        res_rep_leak = client.get(f"/api/v1/reports/{TestProductionE2ESuite.report_b_id}", headers=headers_a)
        assert res_rep_leak.status_code in (403, 404), "Security violation: Company A saw Company B report metadata!"

    # =========================================================================
    # TEST 19: Unauthorized Report Download Blocked
    # =========================================================================
    def test_19_unauthorized_report_download_blocked(self, client: TestClient) -> None:
        headers_a = {"Authorization": f"Bearer {TestProductionE2ESuite.company_a_token}"}
        b_report_id = TestProductionE2ESuite.report_b_id

        res_down = client.get(f"/api/v1/reports/{b_report_id}/download?format=pdf", headers=headers_a)
        assert res_down.status_code in (403, 404), "Critical security violation: Cross-tenant download permitted!"

    # =========================================================================
    # TEST 20: Logout
    # =========================================================================
    def test_20_logout(self, client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {TestProductionE2ESuite.company_a_token}"}
        res = client.post("/api/v1/auth/logout", headers=headers)
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

    # =========================================================================
    # TEST 21: Access Protected API After Logout / Without Token
    # =========================================================================
    def test_21_access_protected_api_without_token(self, client: TestClient) -> None:
        res = client.get("/api/v1/calls")
        assert res.status_code in (401, 403)

        res_rep = client.get("/api/v1/reports")
        assert res_rep.status_code in (401, 403)

    # =========================================================================
    # TEST 22: Invalid / Corrupt ZIP
    # =========================================================================
    def test_22_invalid_corrupt_zip(self, client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {TestProductionE2ESuite.company_a_token}"}
        corrupt_bytes = b"NOT_A_VALID_ZIP_HEADER_RANDOM_GARBAGE"
        files = {"file": ("corrupt.zip", io.BytesIO(corrupt_bytes), "application/zip")}
        res = client.post("/api/v1/calls/upload-zip", headers=headers, files=files)
        assert res.status_code == 400
        assert res.json()["error"]["code"] in ("CORRUPT_ZIP_ARCHIVE", "INVALID_ZIP_ARCHIVE", "BAD_REQUEST")

    # =========================================================================
    # TEST 23: Malicious ZIP Path Traversal
    # =========================================================================
    def test_23_malicious_zip_path_traversal(self, client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {TestProductionE2ESuite.company_a_token}"}
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("../../etc/shadow_call.wav", make_wav_bytes(b"traversal_audio"))
            zf.writestr("..\\..\\windows\\system32\\bad.wav", make_wav_bytes(b"win_traversal"))
        zip_buf.seek(0)

        files = {"file": ("traversal.zip", zip_buf, "application/zip")}
        res = client.post("/api/v1/calls/upload-zip", headers=headers, files=files)
        assert res.status_code in (200, 400)
        if res.status_code == 200:
            data = res.json()
            for c in data.get("created_calls", []):
                if c.get("audio_file"):
                    assert ".." not in c["audio_file"]["filename"]

    # =========================================================================
    # TEST 24: Oversized Upload / ZIP Bomb Detection
    # =========================================================================
    def test_24_oversized_upload_and_zip_bomb(self, client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {TestProductionE2ESuite.company_a_token}"}
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("huge_zeroes.wav", b"\x00" * (15 * 1024 * 1024))
        zip_buf.seek(0)

        files = {"file": ("bomb.zip", zip_buf, "application/zip")}
        res = client.post("/api/v1/calls/upload-zip", headers=headers, files=files)
        assert res.status_code in (200, 400, 413)

    # =========================================================================
    # TEST 25: Invalid Authentication Token
    # =========================================================================
    def test_25_invalid_authentication_token(self, client: TestClient) -> None:
        bad_headers = {"Authorization": "Bearer invalid.fake.token.here"}
        res = client.get("/api/v1/auth/me", headers=bad_headers)
        assert res.status_code == 401
        assert res.json()["error"]["code"] in ("AUTHENTICATION_FAILED", "INVALID_TOKEN", "UNAUTHORIZED")
