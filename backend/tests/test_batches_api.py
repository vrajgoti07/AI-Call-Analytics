"""
AI Call Analytics — Ingestion Batches API & Batch Reports Test Suite.

Validates:
1. ZIP upload creates an IngestionBatch and returns batch_id
2. Batch listing and detail endpoints
3. Batch-scoped call listing and calls?batch_id filtering
4. BATCH_ANALYTICS report generation and multi-format download
5. Workspace/company tenant isolation on batches
"""

from __future__ import annotations

import io
import uuid
import zipfile
import pytest
from starlette.testclient import TestClient

from backend.app.main import app


def make_wav_bytes(content: bytes = b"\x00\x00\x00\x00") -> bytes:
    """Construct a minimal valid 16-bit 16kHz mono WAV file."""
    data_len = len(content)
    file_len = 36 + data_len
    header = bytearray(b"RIFF")
    header.extend(file_len.to_bytes(4, "little"))
    header.extend(b"WAVEfmt ")
    header.extend((16).to_bytes(4, "little"))
    header.extend((1).to_bytes(2, "little"))       # PCM
    header.extend((1).to_bytes(2, "little"))       # 1 channel
    header.extend((16000).to_bytes(4, "little"))   # 16000 Hz
    header.extend((32000).to_bytes(4, "little"))   # byte rate
    header.extend((2).to_bytes(2, "little"))       # block align
    header.extend((16).to_bytes(2, "little"))      # bits per sample
    header.extend(b"data")
    header.extend(data_len.to_bytes(4, "little"))
    header.extend(content)
    return bytes(header)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_batch_workflow_and_reports(client):
    suffix = uuid.uuid4().hex[:6]

    # 1. Register & Login
    email = f"batch_admin_{suffix}@test.com"
    pwd = "SecurePassword123!"
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": pwd, "full_name": "Batch Admin", "company_name": f"Batch Co {suffix}"},
    )
    assert reg_resp.status_code == 201

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": pwd},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload a ZIP with 3 valid audio calls
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("audio1.wav", make_wav_bytes(b"\x01\x02" * 100))
        zf.writestr("subfolder/audio2.wav", make_wav_bytes(b"\x03\x04" * 100))
        zf.writestr("audio3.wav", make_wav_bytes(b"\x05\x06" * 100))
    buf.seek(0)

    upload_resp = client.post(
        "/api/v1/calls/upload-zip?auto_analyze=false",
        headers=headers,
        files={"file": ("customer_calls.zip", buf.read(), "application/zip")},
    )
    assert upload_resp.status_code == 200, upload_resp.text
    data = upload_resp.json()
    assert "batch_id" in data
    assert data["batch_id"] is not None
    batch_id = data["batch_id"]
    assert data["processed_count"] == 3
    assert len(data["created_calls"]) == 3

    # Check each call has batch_id
    for call in data["created_calls"]:
        assert call["batch_id"] == batch_id

    # 3. List Batches
    batches_resp = client.get("/api/v1/batches", headers=headers)
    assert batches_resp.status_code == 200
    b_data = batches_resp.json()
    assert b_data["pagination"]["total"] >= 1
    matching_batch = next((b for b in b_data["items"] if b["id"] == batch_id), None)
    assert matching_batch is not None
    assert matching_batch["original_filename"] == "customer_calls.zip"
    assert matching_batch["total_files"] == 3
    assert matching_batch["processed_count"] == 3

    # 4. Get Batch Detail
    batch_detail_resp = client.get(f"/api/v1/batches/{batch_id}", headers=headers)
    assert batch_detail_resp.status_code == 200
    bd = batch_detail_resp.json()
    assert bd["id"] == batch_id
    assert bd["total_files"] == 3

    # 5. List Batch Calls via /batches/{id}/calls
    batch_calls_resp = client.get(f"/api/v1/batches/{batch_id}/calls", headers=headers)
    assert batch_calls_resp.status_code == 200
    bc = batch_calls_resp.json()
    assert bc["pagination"]["total"] == 3
    for c in bc["items"]:
        assert c["batch_id"] == batch_id

    # 6. Filter Calls via /calls?batch_id={batch_id}
    filter_calls_resp = client.get(f"/api/v1/calls?batch_id={batch_id}", headers=headers)
    assert filter_calls_resp.status_code == 200
    fc = filter_calls_resp.json()
    assert fc["pagination"]["total"] == 3

    # 7. Generate BATCH_ANALYTICS Report
    report_resp = client.post(
        f"/api/v1/batches/{batch_id}/reports",
        headers=headers,
        json={"title": "Q3 Customer Batch Analytics"},
    )
    assert report_resp.status_code == 201, report_resp.text
    r_data = report_resp.json()
    report_id = r_data["id"]
    assert r_data["report_type"] == "BATCH_ANALYTICS"
    assert r_data["batch_id"] == batch_id
    assert r_data["status"] == "COMPLETED"
    assert r_data["has_pdf"] is True
    assert r_data["has_json"] is True
    assert r_data["has_csv"] is True

    # 8. Download Report Artifacts
    pdf_dl = client.get(f"/api/v1/reports/{report_id}/download?format=pdf", headers=headers)
    assert pdf_dl.status_code == 200
    assert pdf_dl.headers["content-type"] == "application/pdf"
    assert len(pdf_dl.content) > 100

    csv_dl = client.get(f"/api/v1/reports/{report_id}/download?format=csv", headers=headers)
    assert csv_dl.status_code == 200
    assert "Call ID" in csv_dl.text

    json_dl = client.get(f"/api/v1/reports/{report_id}/download?format=json", headers=headers)
    assert json_dl.status_code == 200
    j_content = json_dl.json()
    assert j_content["batch_id"] == batch_id
    assert j_content["total_calls"] == 3

    # 9. Tenant Isolation: Second company cannot access this batch or its reports
    other_email = f"other_{suffix}@test.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": other_email, "password": pwd, "full_name": "Other Admin", "company_name": f"Other Co {suffix}"},
    )
    other_login = client.post("/api/v1/auth/login", json={"email": other_email, "password": pwd})
    assert other_login.status_code == 200
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    # Attempt to view batch -> 404
    assert client.get(f"/api/v1/batches/{batch_id}", headers=other_headers).status_code == 404
    # Attempt to view batch calls -> 404
    assert client.get(f"/api/v1/batches/{batch_id}/calls", headers=other_headers).status_code == 404
    # Attempt to download batch report -> 404
    assert client.get(f"/api/v1/reports/{report_id}/download", headers=other_headers).status_code == 404
