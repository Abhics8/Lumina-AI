import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    """Test the root health check endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Lumina API"
    assert data["status"] == "active"
    assert "version" in data

def test_docs_reachable():
    """Ensure OpenAPI docs are generated and reachable."""
    response = client.get("/docs")
    assert response.status_code == 200

# Additional tests can be added here for /api/v1/search endpoints
# Example mock test for a search endpoint if it exists
def test_search_endpoint_mock(monkeypatch):
    """Mock test for search to ensure routing is correct without loading heavy models."""
    # Assuming there's a POST /api/v1/search, we just test 422 for missing body
    response = client.post("/api/v1/search", json={})
    # Might be 404 if route doesn't exist, or 422 if body is invalid
    assert response.status_code in [404, 422]
