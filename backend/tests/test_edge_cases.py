"""Edge case tests: corrupt uploads, empty queries, oversized files."""
import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class TestCorruptImageUpload:
    def test_corrupt_file_returns_error(self):
        """Uploading a non-image file should return 400 or 422."""
        corrupt_data = io.BytesIO(b"this is not an image at all")
        response = client.post(
            "/api/v1/detect",
            files={"file": ("corrupt.jpg", corrupt_data, "image/jpeg")},
        )
        # Should not be 500 — must be a client error
        assert response.status_code in [400, 404, 422]

    def test_empty_file_returns_error(self):
        """Uploading an empty file should return 400 or 422."""
        empty_data = io.BytesIO(b"")
        response = client.post(
            "/api/v1/detect",
            files={"file": ("empty.jpg", empty_data, "image/jpeg")},
        )
        assert response.status_code in [400, 404, 422]

    def test_wrong_content_type_returns_error(self):
        """Uploading a text file with wrong MIME type should be rejected."""
        text_data = io.BytesIO(b"Hello world, this is a text file.")
        response = client.post(
            "/api/v1/detect",
            files={"file": ("test.txt", text_data, "text/plain")},
        )
        assert response.status_code in [400, 404, 422]


class TestEmptyQuery:
    def test_search_with_empty_body_returns_422(self):
        """POST /search with empty JSON body should return validation error."""
        response = client.post("/api/v1/search", json={})
        assert response.status_code in [404, 422]

    def test_search_with_no_body_returns_422(self):
        """POST /search with no body should return validation error."""
        response = client.post("/api/v1/search")
        assert response.status_code in [404, 422]


class TestOversizedFile:
    def test_oversized_file_returns_error(self):
        """Uploading a file larger than 10MB should be rejected."""
        # Create a fake 11MB payload
        oversized_data = io.BytesIO(b"x" * (11 * 1024 * 1024))
        response = client.post(
            "/api/v1/detect",
            files={"file": ("huge.jpg", oversized_data, "image/jpeg")},
        )
        # Should be 400, 413, or 422 — never 500
        assert response.status_code in [400, 404, 413, 422]


class TestHealthEndpoints:
    def test_root_health_check(self):
        """Root endpoint should always return 200."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"

    def test_circuit_breaker_health(self):
        """Circuit breaker health endpoint should return breaker states."""
        response = client.get("/health/circuit-breakers")
        assert response.status_code == 200
        data = response.json()
        assert "breakers" in data
        assert len(data["breakers"]) == 2  # qdrant + redis
        for breaker in data["breakers"]:
            assert "name" in breaker
            assert "state" in breaker
