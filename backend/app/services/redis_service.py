import json
import logging
import redis.asyncio as redis
from typing import Optional, Any
from app.core.config import settings
from app.core.circuit_breaker import redis_breaker, CircuitOpenError

logger = logging.getLogger(__name__)


class RedisService:
    _client: Optional[redis.Redis] = None

    @classmethod
    async def get_client(cls) -> redis.Redis:
        if cls._client is None:
            cls._client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=3,
                retry_on_timeout=True,
            )
        return cls._client

    @classmethod
    async def get_cache(cls, key: str) -> Optional[dict[str, Any]]:
        """
        Get cached value. Returns None on cache miss OR if Redis is unavailable.
        Never raises — callers treat a Redis failure as a cache miss.
        """
        try:
            client = await redis_breaker.call(cls.get_client)
            data = await redis_breaker.call(client.get, key)
            if data:
                return json.loads(data)
            return None
        except CircuitOpenError:
            logger.warning("Redis circuit open — treating as cache miss for key=%s", key)
            return None
        except (redis.ConnectionError, redis.TimeoutError, OSError) as exc:
            logger.warning("Redis unavailable — cache miss for key=%s: %s", key, exc)
            return None
        except Exception as exc:
            logger.error("Unexpected Redis error for key=%s: %s", key, exc)
            return None

    @classmethod
    async def set_cache(cls, key: str, value: Any, expire: int = 3600) -> bool:
        """
        Set cached value. Returns False if Redis is unavailable.
        Never raises — cache writes are best-effort.
        """
        try:
            client = await redis_breaker.call(cls.get_client)
            await redis_breaker.call(client.set, key, json.dumps(value), ex=expire)
            return True
        except CircuitOpenError:
            logger.debug("Redis circuit open — skipping cache write for key=%s", key)
            return False
        except (redis.ConnectionError, redis.TimeoutError, OSError) as exc:
            logger.warning("Redis unavailable — skipping cache write for key=%s: %s", key, exc)
            return False
        except Exception as exc:
            logger.error("Unexpected Redis error on write for key=%s: %s", key, exc)
            return False

    @classmethod
    async def close(cls) -> None:
        if cls._client:
            try:
                await cls._client.close()
            except Exception:
                pass
            cls._client = None
