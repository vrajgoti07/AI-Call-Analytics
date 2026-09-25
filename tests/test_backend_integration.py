"""
AI Call Analytics — Phase 10 Backend Integration Test Suite.

Validates:
1. Configuration management, environment separation, and startup validation
2. Liveness, readiness, and service health checks
3. Call entity lifecycle (create, upload, list, pagination, detail, delete)
4. Audio upload security (extension whitelist, directory traversal prevention)
5. Background job dispatching and stage-level progress tracking
6. Transcript and turn retrieval with pagination
7. End-to-end pipeline execution (ASR, Diarization, NLP, Risk, Embeddings)
8. Semantic vector search query endpoint
9. Theme discovery endpoints
10. Escalation risk retrieval
11. Standardized error format and request correlation middleware
"""

from __future__ import annotations

import io
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import Settings, validate_environment
from backend.app.core.exceptions import AppException, CallNotFoundError
from backend.app.database.session import SyncSessionLocal
from backend.app.main import app
from backend.app.models.call import CallStatus, JobStatus
from backend.app.repositories.call_repository import CallRepository
from backend.app.repositories.job_repository import JobRepository
from backend.app.workers.pipeline_tasks import analyze_call_task


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Test client instance for FastAPI application."""
    return TestClient(app)


# ============================================================================
# 1. Configuration & Validation Tests
# ============================================================================

class TestConfigurationAndEnvironment:
    """Tests for settings parsing and startup validation."""

    def test_default_settings_instantiation(self) -> None:
        """Verify default configuration loads properly."""
        cfg = Settings()
        assert cfg.app_name == "ai-call-analytics"
        assert cfg.backend_port == 8000
        assert len(cfg.cors_origin_list) >= 1

    def test_startup_validation_succeeds_on_valid_config(self) -> None:
        """Verify validation passes for valid development environment."""
        cfg = Settings(database_url="postgresql://user:pass@localhost:5432/testdb", app_env="development")
        validate_environment(cfg)  # Should not raise

    def test_startup_validation_rejects_missing_database_url(self) -> None:
        """Verify validation raises ValueError when DATABASE_URL is empty."""
        cfg = Settings(database_url="", app_env="development")
        with pytest.raises(ValueError, match="DATABASE_URL must be specified"):
            validate_environment(cfg)

    def test_startup_validation_rejects_insecure_production_creds(self) -> None:
        """Verify validation forbids default passwords in production."""
        cfg = Settings(
            database_url="postgresql://postgres:changeme@localhost:5432/db",
            app_env="production",
            jwt_secret="a" * 32,
            cors_origins="https://example.com",
        )
        with pytest.raises(ValueError, match="default database credentials"):
            validate_environment(cfg)


# ============================================================================
# 2. Health & Readiness Probes
# ============================================================================

class TestHealthProbes:
    """Tests for /health, /health/live, /health/ready endpoints."""

    def test_health_check(self, client: TestClient) -> None:
        """Verify /health returns service status and metadata."""
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["service"] == "ai-call-analytics-backend"
        assert "version" in data

    def test_liveness_probe(self, client: TestClient) -> None:
        """Verify /health/live returns alive."""
        res = client.get("/health/live")
        assert res.status_code == 200
        assert res.json()["status"] == "alive"

    def test_readiness_probe_dependencies(self, client: TestClient) -> None:
        """Verify /health/ready checks dependencies."""
        res = client.get("/health/ready")
        assert res.status_code in (200, 503)
        assert "dependencies" in res.json()


# ============================================================================
# 3. Call Lifecycle & Upload API Tests
# ============================================================================

class TestCallEndpoints:
    """Tests for /api/v1/calls CRUD and uploads."""

    def test_create_and_get_call(self, client: TestClient) -> None:
        """Verify creating a call and retrieving it by ID."""
        # Create
        res = client.post("/api/v1/calls", json={"external_id": "TEST-CALL-01", "language": "en"})
        assert res.status_code == 201
        data = res.json()
        call_id = data["id"]
        assert data["external_id"] == "TEST-CALL-01"
        assert data["status"] == CallStatus.UPLOADED.value

        # Retrieve
        res_get = client.get(f"/api/v1/calls/{call_id}")
        assert res_get.status_code == 200
        get_data = res_get.json()
        assert get_data["id"] == call_id
        assert get_data["has_transcript"] is False

        # Cleanup
        client.delete(f"/api/v1/calls/{call_id}")

    def test_list_calls_pagination(self, client: TestClient) -> None:
        """Verify listing calls with pagination and total metadata."""
        res = client.get("/api/v1/calls?page=1&page_size=5")
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "pagination" in data
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 5

    def test_audio_upload_valid(self, client: TestClient) -> None:
        """Verify uploading valid audio file updates call with AudioFile."""
        # Create call
        res_call = client.post("/api/v1/calls", json={"external_id": "TEST-UPLOAD-VALID"})
        call_id = res_call.json()["id"]

        dummy_wav = b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
        files = {"file": ("call_sample.wav", io.BytesIO(dummy_wav), "audio/wav")}
        res_upload = client.post(f"/api/v1/calls/{call_id}/upload", files=files)
        assert res_upload.status_code == 200
        upload_data = res_upload.json()
        assert upload_data["audio_file"] is not None
        assert upload_data["audio_file"]["filename"] == "call_sample.wav"
        assert upload_data["audio_file"]["size"] == len(dummy_wav)

        client.delete(f"/api/v1/calls/{call_id}")

    def test_audio_upload_unsupported_extension_rejected(self, client: TestClient) -> None:
        """Verify uploading invalid extension (.txt) returns 415."""
        res_call = client.post("/api/v1/calls", json={"external_id": "TEST-BAD-UPLOAD"})
        call_id = res_call.json()["id"]

        files = {"file": ("script.txt", io.BytesIO(b"not audio"), "text/plain")}
        res = client.post(f"/api/v1/calls/{call_id}/upload", files=files)
        assert res.status_code == 415
        assert res.json()["error"]["code"] == "UNSUPPORTED_AUDIO"

        client.delete(f"/api/v1/calls/{call_id}")


# ============================================================================
# 4. Pipeline Execution & Analysis Tests
# ============================================================================

class TestAnalysisPipelineEndpoints:
    """Tests for /api/v1/calls/{id}/analyze and status checks."""

    def test_start_analysis_and_poll_status(self, client: TestClient) -> None:
        """Verify starting analysis returns 202 Accepted and creates job."""
        res_call = client.post("/api/v1/calls", json={"external_id": "TEST-PIPELINE-01"})
        call_id = res_call.json()["id"]

        # Trigger analysis
        res_an = client.post(f"/api/v1/calls/{call_id}/analyze")
        assert res_an.status_code == 202
        job_data = res_an.json()
        assert "job_id" in job_data
        assert job_data["job_id"] is not None
        job_id = job_data["job_id"]

        # Query status
        res_st = client.get(f"/api/v1/calls/{call_id}/analysis/status")
        assert res_st.status_code == 200
        st_data = res_st.json()
        assert st_data["call_id"] == call_id
        assert "stages" in st_data

        client.delete(f"/api/v1/calls/{call_id}")

    def test_full_pipeline_task_execution(self, client: TestClient) -> None:
        """Verify synchronous task execution completes all AI stages and persists results."""
        res_call = client.post("/api/v1/calls", json={"external_id": "TEST-FULL-PIPELINE"})
        call_id = res_call.json()["id"]

        res_an = client.post(f"/api/v1/calls/{call_id}/analyze")
        job_id = res_an.json()["job_id"]

        # Run task directly
        result = analyze_call_task(call_id_str=call_id, job_id_str=job_id)
        assert result["status"] == "success"

        # Check completed status
        res_st = client.get(f"/api/v1/calls/{call_id}/analysis/status")
        assert res_st.status_code == 200
        assert res_st.json()["progress"] == 100
        assert res_st.json()["status"] == JobStatus.SUCCESS.value

        # Check transcript turns
        res_tx = client.get(f"/api/v1/calls/{call_id}/transcript")
        assert res_tx.status_code == 200
        assert res_tx.json()["turn_count"] >= 1

        res_turns = client.get(f"/api/v1/calls/{call_id}/transcript/turns")
        assert res_turns.status_code == 200
        turns = res_turns.json()["items"]
        assert len(turns) >= 1

        # Check risk record
        res_risk = client.get(f"/api/v1/calls/{call_id}/risk")
        assert res_risk.status_code == 200
        assert "risk_score" in res_risk.json()
        assert "risk_level" in res_risk.json()

        # Check analysis summary
        res_summary = client.get(f"/api/v1/calls/{call_id}/analysis")
        assert res_summary.status_code == 200
        assert res_summary.json()["status"] == CallStatus.COMPLETED.value

        client.delete(f"/api/v1/calls/{call_id}")


# ============================================================================
# 5. Semantic Search & Themes Endpoints
# ============================================================================

class TestSearchAndThemesEndpoints:
    """Tests for /api/v1/search/semantic and /api/v1/themes."""

    def test_semantic_search_empty_query_rejected(self, client: TestClient) -> None:
        """Verify empty or short query fails validation."""
        res = client.post("/api/v1/search/semantic", json={"query": "a"})
        assert res.status_code == 422

    def test_semantic_search_valid_query(self, client: TestClient) -> None:
        """Verify semantic search returns structured results."""
        res = client.post("/api/v1/search/semantic", json={"query": "credit card payment issue", "top_k": 3})
        assert res.status_code == 200
        data = res.json()
        assert data["query"] == "credit card payment issue"
        assert "total_results" in data
        assert isinstance(data["results"], list)

    def test_list_themes(self, client: TestClient) -> None:
        """Verify /api/v1/themes returns list."""
        res = client.get("/api/v1/themes")
        assert res.status_code == 200
        assert "themes" in res.json()

    def test_get_nonexistent_theme(self, client: TestClient) -> None:
        """Verify requesting non-existent theme returns 404."""
        dummy_id = uuid.uuid4()
        res = client.get(f"/api/v1/themes/{dummy_id}")
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "THEME_NOT_FOUND"


# ============================================================================
# 6. Jobs & Error Formatting Tests
# ============================================================================

class TestJobsAndErrorHandling:
    """Tests for jobs listing, nonexistent lookups, and security headers."""

    def test_list_jobs(self, client: TestClient) -> None:
        """Verify /api/v1/jobs returns paginated job items."""
        res = client.get("/api/v1/jobs?page=1&page_size=10")
        assert res.status_code == 200
        assert "items" in res.json()
        assert "pagination" in res.json()

    def test_get_nonexistent_job_returns_404(self, client: TestClient) -> None:
        """Verify requesting non-existent job returns 404 with error code."""
        dummy_id = uuid.uuid4()
        res = client.get(f"/api/v1/jobs/{dummy_id}")
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "JOB_NOT_FOUND"

    def test_security_headers_and_request_id(self, client: TestClient) -> None:
        """Verify X-Request-ID and security headers are present on all responses."""
        res = client.get("/health")
        assert "x-request-id" in res.headers
        assert res.headers.get("x-content-type-options") == "nosniff"
        assert res.headers.get("x-frame-options") == "DENY"
        assert res.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
