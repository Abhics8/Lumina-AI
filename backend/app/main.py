import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.api_router import api_router
from app.core.config import settings
from app.core.circuit_breaker import qdrant_breaker, redis_breaker
from app.services.redis_service import RedisService

logger = logging.getLogger(__name__)

# Rate limiter: 60 requests/minute per IP
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown events."""
    logger.info("Lumina API starting up...")
    yield
    logger.info("Lumina API shutting down — closing Redis connection...")
    await RedisService.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Intelligent Visual Commerce Engine powered by Owlv2 & SigLIP",
    version="0.2.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def health_check() -> dict:
    return {
        "service": "Lumina API",
        "status": "active",
        "version": "0.2.0",
    }


@app.get("/health/circuit-breakers")
def circuit_breaker_status() -> dict:
    """Expose circuit breaker states for monitoring."""
    return {
        "breakers": [
            qdrant_breaker.status(),
            redis_breaker.status(),
        ]
    }
