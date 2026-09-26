"""
AI Call Analytics — EXACTLY TWO ROLES: ADMIN + COMPANY Test Suite.

Validates:
1. Admin bootstrap authentication (vrajgoti07@gmail.com / 123456789)
2. Admin permissions: /admin/companies, /jobs, /evaluation
3. Company public registration strictly generates role='COMPANY'
4. IDOR isolation: Company A cannot read Company B batch, call, audio, transcript, report
5. Company B cannot access Company A resources
6. Route protection: Company accounts get 403 on admin-only endpoints
7. Company deactivation by Admin prevents Company login and token usage
8. Forgot & Reset password flow
"""

from __future__ import annotations

import io
import uuid
import zipfile
import pytest
from starlette.testclient import TestClient

from backend.app.main import app


def make_dummy_wav() -> bytes:
    """Construct minimal valid WAV header."""
    header = bytearray(b"RIFF")
    header.extend((36 + 4).to_bytes(4, "little"))
    header.extend(b"WAVEfmt ")
    header.extend((16).to_bytes(4, "little"))
    header.extend((1).to_bytes(2, "little"))
    header.extend((1).to_bytes(2, "little"))
    header.extend((16000).to_bytes(4, "little"))
    header.extend((32000).to_bytes(4, "little"))
    header.extend((2).to_bytes(2, "little"))
    header.extend((16).to_bytes(2, "little"))
    header.extend(b"data")
    header.extend((4).to_bytes(4, "little"))
    header.extend(b"\x00\x00\x00\x00")
    return bytes(header)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_admin_bootstrap_and_permissions(client: TestClient):
    """Test 1: Admin bootstrap account login and admin-only endpoint access."""
    # 1. Login with bootstrap credentials
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "vrajgoti07@gmail.com", "password": "123456789"},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    data = resp.json()
    token = data["access_token"]
    user = data["user"]
    assert user["role"] == "ADMIN"
    assert user["email"] == "vrajgoti07@gmail.com"

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Access Admin Companies endpoint
    comp_resp = client.get("/api/v1/admin/companies", headers=headers)
    assert comp_resp.status_code == 200
    assert isinstance(comp_resp.json(), list)

    # 3. Access Jobs endpoint (Admin only)
    jobs_resp = client.get("/api/v1/jobs", headers=headers)
    assert jobs_resp.status_code == 200
    assert "items" in jobs_resp.json()


def test_company_registration_and_isolation(client: TestClient):
    """Test 2: Company registration creates COMPANY role, and cross-company IDOR is blocked."""
    suffix = uuid.uuid4().hex[:6]

    # Register Company A
    email_a = f"company_a_{suffix}@test.com"
    pwd = "CompanyPassword123!"
    reg_a = client.post(
        "/api/v1/auth/register",
        json={
            "email": email_a,
            "password": pwd,
            "full_name": "Alice Admin",
            "company_name": f"Alpha Corp {suffix}",
        },
    )
    assert reg_a.status_code == 201
    user_a = reg_a.json()["user"]
    assert user_a["role"] == "COMPANY"
    assert user_a["company_id"] is not None
    token_a = reg_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register Company B
    email_b = f"company_b_{suffix}@test.com"
    reg_b = client.post(
        "/api/v1/auth/register",
        json={
            "email": email_b,
            "password": pwd,
            "full_name": "Bob Admin",
            "company_name": f"Beta Corp {suffix}",
        },
    )
    assert reg_b.status_code == 201
    user_b = reg_b.json()["user"]
    assert user_b["role"] == "COMPANY"
    assert user_b["company_id"] != user_a["company_id"]
    token_b = reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Company A attempts to access admin endpoints -> Must return 403
    assert client.get("/api/v1/admin/companies", headers=headers_a).status_code == 403
    assert client.get("/api/v1/jobs", headers=headers_a).status_code == 403
    assert client.get("/api/v1/evaluation", headers=headers_a).status_code == 403

    # Company A uploads a ZIP to create Batch A and Call A
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("call_alpha_1.wav", make_dummy_wav())
    zip_buffer.seek(0)

    upload_resp = client.post(
        "/api/v1/calls/upload-zip?auto_analyze=false",
        files={"file": (f"calls_a_{suffix}.zip", zip_buffer.getvalue(), "application/zip")},
        headers=headers_a,
    )
    assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
    batch_a_id = upload_resp.json()["batch_id"]
    calls_a = upload_resp.json()["created_calls"]
    assert len(calls_a) > 0
    call_a_id = calls_a[0]["id"]

    # Company A generates a report for Call A
    rep_resp = client.post(
        "/api/v1/reports/generate",
        json={
            "report_type": "INDIVIDUAL_CALL",
            "call_id": call_a_id,
            "title": f"Report Call A {suffix}",
        },
        headers=headers_a,
    )
    assert rep_resp.status_code == 201
    report_a_id = rep_resp.json()["id"]

    # --- IDOR CHECKS: Company B attempts to access Company A resources ---
    # 1. Batch A access by Company B -> 404
    assert client.get(f"/api/v1/batches/{batch_a_id}", headers=headers_b).status_code == 404
    assert client.get(f"/api/v1/batches/{batch_a_id}/calls", headers=headers_b).status_code == 404

    # 2. Call A access by Company B -> 404
    assert client.get(f"/api/v1/calls/{call_a_id}", headers=headers_b).status_code == 404
    assert client.get(f"/api/v1/calls/{call_a_id}/audio", headers=headers_b).status_code == 404
    assert client.get(f"/api/v1/calls/{call_a_id}/transcript", headers=headers_b).status_code == 404

    # 3. Report A access by Company B -> 404
    assert client.get(f"/api/v1/reports/{report_a_id}", headers=headers_b).status_code == 404

    # --- Verify Company A CAN access its own resources ---
    assert client.get(f"/api/v1/batches/{batch_a_id}", headers=headers_a).status_code == 200
    assert client.get(f"/api/v1/calls/{call_a_id}", headers=headers_a).status_code == 200
    assert client.get(f"/api/v1/reports/{report_a_id}", headers=headers_a).status_code == 200


def test_company_deactivation_flow(client: TestClient):
    """Test 3: Admin deactivates a company -> company users cannot login or access APIs."""
    suffix = uuid.uuid4().hex[:6]
    email = f"deact_user_{suffix}@test.com"
    pwd = "DeactPassword123!"

    # 1. Register company
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": pwd,
            "full_name": "Deact Member",
            "company_name": f"Deact Co {suffix}",
        },
    )
    assert reg.status_code == 201
    company_id = reg.json()["user"]["company_id"]
    token = reg.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {token}"}

    # Verify user can access /api/v1/calls initially
    assert client.get("/api/v1/calls", headers=user_headers).status_code == 200

    # 2. Admin logs in
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "vrajgoti07@gmail.com", "password": "123456789"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    # 3. Admin deactivates company
    deact_resp = client.patch(
        f"/api/v1/admin/companies/{company_id}/status",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert deact_resp.status_code == 200
    assert deact_resp.json()["is_active"] is False

    # 4. User attempts login -> Must fail with 403 Forbidden
    login_attempt = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": pwd},
    )
    assert login_attempt.status_code == 403
    assert "disabled" in login_attempt.text.lower()

    # 5. User attempts API request with existing token -> Must fail with 401 or 403
    call_attempt = client.get("/api/v1/calls", headers=user_headers)
    assert call_attempt.status_code in (401, 403)


def test_forgot_and_reset_password(client: TestClient):
    """Test 4: Forgot password request and reset password."""
    suffix = uuid.uuid4().hex[:6]
    email = f"pwd_reset_{suffix}@test.com"
    old_pwd = "OldPassword123!"
    new_pwd = "NewSecurePassword456!"

    # 1. Register account
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": old_pwd,
            "full_name": "Reset User",
            "company_name": f"Reset Co {suffix}",
        },
    )
    assert reg.status_code == 201

    # 2. Forgot password request
    forgot_resp = client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert forgot_resp.status_code == 200
    assert "message" in forgot_resp.json()

    # 3. Reset password
    reset_resp = client.post(
        "/api/v1/auth/reset-password",
        json={"email": email, "new_password": new_pwd},
    )
    assert reset_resp.status_code == 200

    # 4. Login with old password -> Must fail
    bad_login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": old_pwd},
    )
    assert bad_login.status_code == 401

    # 5. Login with new password -> Must succeed
    good_login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": new_pwd},
    )
    assert good_login.status_code == 200
    assert good_login.json()["user"]["email"] == email
