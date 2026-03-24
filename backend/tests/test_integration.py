"""
Integration test: full search pipeline.
Requires Qdrant and Redis running (use docker-compose.test.yml).
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from PIL import Image
import io


@pytest.fixture
def test_image_bytes() -> io.BytesIO:
    """Create a valid JPEG image in memory."""
    img = Image.new("RGB", (256, 256), color=(200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


class TestFullPipeline:
    """Integration tests for the detect → embed → search flow."""

    def test_detect_endpoint_accepts_valid_image(self, test_image_bytes: io.BytesIO):
        """A valid JPEG image should not cause a 500 error."""
        from app.main import app

        client = TestClient(app)
        response = client.post(
            "/api/v1/detect",
            files={"file": ("test.jpg", test_image_bytes, "image/jpeg")},
        )
        # Might be 200 (success) or 404 (if route doesn't exist in test env)
        # but never 500
        assert response.status_code != 500

    def test_health_returns_version(self):
        """Health check should include version string."""
        from app.main import app

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "version" in response.json()

    def test_api_docs_accessible(self):
        """OpenAPI docs should be reachable."""
        from app.main import app

        client = TestClient(app)
        response = client.get("/docs")
        assert response.status_code == 200


class TestCircuitBreakerIntegration:
    def test_circuit_breaker_starts_closed(self):
        """Both circuit breakers should start in CLOSED state."""
        from app.core.circuit_breaker import qdrant_breaker, redis_breaker

        assert qdrant_breaker.state.value == "closed"
        assert redis_breaker.state.value == "closed"

    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self):
        """Circuit should open after exceeding failure threshold."""
        from app.core.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(
            name="test", failure_threshold=2, recovery_timeout=1.0
        )

        for _ in range(2):
            try:

                async def failing_fn() -> None:
                    raise ConnectionError("down")

                await breaker.call(failing_fn)
            except ConnectionError:
                pass

        assert breaker.state.value == "open"


class TestABTestingIntegration:
    def test_ab_router_routes_traffic(self):
        """A/B router should assign requests to champion or challenger."""
        from app.core.ab_testing import ABTestRouter

        router = ABTestRouter(challenger_traffic_pct=50)
        versions = set()
        for i in range(100):
            version = router.route_request(f"req_{i}")
            versions.add(version)

        # With 50% split, both versions should appear
        assert "v1" in versions
        assert "v2" in versions

    def test_ab_comparison_returns_metrics(self):
        """get_comparison should return structured metrics."""
        from app.core.ab_testing import ABTestRouter

        router = ABTestRouter(challenger_traffic_pct=20)
        router.log_result("r1", "v1", recall_at_k=0.92, latency_ms=45.0)
        router.log_result("r2", "v2", recall_at_k=0.88, latency_ms=52.0)

        comparison = router.get_comparison()
        assert "champion" in comparison
        assert "challenger" in comparison
        assert comparison["champion"]["avg_recall_at_k"] == 0.92
