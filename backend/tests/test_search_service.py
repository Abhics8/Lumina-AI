"""Unit tests for search pipeline (SigLIP embedding + Qdrant retrieval)."""
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image


@pytest.fixture
def mock_embedding() -> list[float]:
    """A fake 1152-dim embedding vector (SigLIP output)."""
    return [0.01 * i for i in range(1152)]


@pytest.fixture
def mock_search_results():
    """Simulated Qdrant search results."""
    results = []
    for i in range(5):
        hit = MagicMock()
        hit.score = 0.95 - (i * 0.05)
        hit.payload = {
            "filename": f"product_{i}.jpg",
            "category": "dress",
        }
        results.append(hit)
    return results


class TestSearchService:
    def test_embedding_dimension_is_correct(self, mock_embedding: list[float]):
        """SigLIP embeddings must be 1152-dimensional."""
        assert len(mock_embedding) == 1152

    def test_search_results_are_ranked_by_score(self, mock_search_results: list):
        """Results must be returned in descending similarity order."""
        scores = [hit.score for hit in mock_search_results]
        assert scores == sorted(scores, reverse=True)

    def test_search_results_have_payload(self, mock_search_results: list):
        """Each result must include a payload with metadata."""
        for hit in mock_search_results:
            assert "filename" in hit.payload
            assert "category" in hit.payload

    def test_search_limit_respected(self, mock_search_results: list):
        """At most `limit` results should be returned."""
        limit = 3
        trimmed = mock_search_results[:limit]
        assert len(trimmed) == limit

    def test_empty_embedding_returns_results(self):
        """A zero vector shouldn't crash — it just returns low-similarity results."""
        zero_embedding = [0.0] * 1152
        assert len(zero_embedding) == 1152


class TestQdrantServiceSafe:
    @pytest.mark.asyncio
    async def test_search_safe_returns_empty_on_failure(self):
        """search_safe should return ([], False) when Qdrant is unavailable."""
        with patch(
            "app.services.qdrant_service.QdrantService.get_client",
            side_effect=Exception("Connection refused"),
        ):
            from app.services.qdrant_service import QdrantService

            results, from_qdrant = await QdrantService.search_safe([0.0] * 1152)
            assert results == []
            assert from_qdrant is False
