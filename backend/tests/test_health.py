"""
Unit tests for FastAPI backend health check endpoint.
"""

import unittest
from starlette.testclient import TestClient

from backend.app.main import app


class TestHealthEndpoint(unittest.TestCase):
    """Test suite for the GET /health endpoint."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health_check_returns_200(self) -> None:
        """Verify GET /health returns HTTP 200."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

    def test_health_check_payload(self) -> None:
        """Verify GET /health response payload matches specification."""
        response = self.client.get("/health")
        data = response.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("service"), "ai-call-analytics-backend")


if __name__ == "__main__":
    unittest.main()
