"""
Circuit Breaker Pattern for external service resilience.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Service is down, fail fast without calling
- HALF_OPEN: Testing if service recovered

Usage:
    breaker = CircuitBreaker(name="qdrant", failure_threshold=5, recovery_timeout=30)
    try:
        result = await breaker.call(async_function, *args)
    except CircuitOpenError:
        # Service is down, return fallback
"""

import asyncio
import time
import logging
from enum import Enum
from typing import Any, Callable, TypeVar, Optional
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open and requests are being rejected."""

    def __init__(self, name: str, retry_after: float) -> None:
        self.name = name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker '{name}' is OPEN. Retry after {retry_after:.0f}s."
        )


class CircuitBreaker:
    """
    Circuit breaker with configurable thresholds and automatic recovery.

    Args:
        name: Identifier for this breaker (e.g., "qdrant", "redis")
        failure_threshold: Number of consecutive failures before opening
        recovery_timeout: Seconds to wait before attempting recovery
        half_open_max_calls: Max calls allowed in half-open state
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._last_failure_time: float = 0.0
        self._half_open_calls: int = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info(
                    "Circuit '%s' transitioning OPEN → HALF_OPEN after %.0fs",
                    self.name,
                    elapsed,
                )
        return self._state

    @property
    def retry_after(self) -> float:
        if self._state != CircuitState.OPEN:
            return 0.0
        elapsed = time.monotonic() - self._last_failure_time
        return max(0.0, self.recovery_timeout - elapsed)

    def status(self) -> dict[str, Any]:
        """Return current breaker status for health endpoint."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "retry_after_seconds": round(self.retry_after, 1),
        }

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute function through the circuit breaker."""
        async with self._lock:
            current_state = self.state

            if current_state == CircuitState.OPEN:
                raise CircuitOpenError(self.name, self.retry_after)

            if (
                current_state == CircuitState.HALF_OPEN
                and self._half_open_calls >= self.half_open_max_calls
            ):
                raise CircuitOpenError(self.name, self.recovery_timeout)

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as exc:
            await self._on_failure(exc)
            raise

    async def _on_success(self) -> None:
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info(
                    "Circuit '%s' recovered: HALF_OPEN → CLOSED", self.name
                )
            self._state = CircuitState.CLOSED
            self._failure_count = 0

    async def _on_failure(self, exc: Exception) -> None:
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit '%s' re-opened after half-open failure: %s",
                    self.name,
                    exc,
                )
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit '%s' OPENED after %d consecutive failures: %s",
                    self.name,
                    self._failure_count,
                    exc,
                )


# Global circuit breaker instances
qdrant_breaker = CircuitBreaker(
    name="qdrant", failure_threshold=5, recovery_timeout=30.0
)
redis_breaker = CircuitBreaker(
    name="redis", failure_threshold=3, recovery_timeout=15.0
)
