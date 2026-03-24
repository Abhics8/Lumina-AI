import uuid
import logging
from typing import Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from app.core.config import settings
from app.core.circuit_breaker import qdrant_breaker, CircuitOpenError

logger = logging.getLogger(__name__)


class QdrantService:
    _client: Optional[QdrantClient] = None

    @classmethod
    def get_client(cls) -> QdrantClient:
        if cls._client is None:
            cls._client = QdrantClient(
                url=settings.QDRANT_URL,
                timeout=10,
            )
        return cls._client

    @staticmethod
    def init_collection() -> None:
        client = QdrantService.get_client()
        if not client.collection_exists(settings.QDRANT_COLLECTION):
            client.create_collection(
                collection_name=settings.QDRANT_COLLECTION,
                vectors_config=VectorParams(size=1152, distance=Distance.COSINE),
            )
            logger.info("Collection '%s' created.", settings.QDRANT_COLLECTION)

    @staticmethod
    def upsert_item(embedding: list[float], payload: dict[str, Any]) -> str:
        """Upsert a single item. Raises on Qdrant failure (upstream should catch)."""
        client = QdrantService.get_client()
        point_id = str(uuid.uuid4())

        client.upsert(
            collection_name=settings.QDRANT_COLLECTION,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
            ],
        )
        return point_id

    @staticmethod
    async def search_safe(
        embedding: list[float],
        limit: int = 5,
    ) -> tuple[list[Any], bool]:
        """
        Search with circuit breaker protection.

        Returns:
            (results, from_qdrant): results list and whether they came from Qdrant.
            If Qdrant is down, returns ([], False).
        """
        try:
            client = QdrantService.get_client()
            results = await qdrant_breaker.call(
                client.search,
                collection_name=settings.QDRANT_COLLECTION,
                query_vector=embedding,
                limit=limit,
            )
            return results, True
        except CircuitOpenError as exc:
            logger.warning(
                "Qdrant circuit open — returning empty results. Retry after %.0fs",
                exc.retry_after,
            )
            return [], False
        except Exception as exc:
            logger.error("Qdrant search failed: %s", exc)
            return [], False

    @staticmethod
    def search(embedding: list[float], limit: int = 5) -> list[Any]:
        """Original synchronous search (kept for backward compatibility)."""
        client = QdrantService.get_client()
        results = client.search(
            collection_name=settings.QDRANT_COLLECTION,
            query_vector=embedding,
            limit=limit,
        )
        return results
