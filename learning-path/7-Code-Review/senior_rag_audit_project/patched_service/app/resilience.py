"""patched_service/app/resilience.py
Circuit Breaker + Retry с экспоненциальным откатом для LLM API.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Callable, Any, TypeVar
from functools import wraps

logger = logging.getLogger(__name__)
T = TypeVar("T")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit Breaker для защиты от каскадных отказов внешних API.
    CLOSED -> (failure_threshold) -> OPEN -> (recovery_timeout) -> HALF_OPEN -> CLOSED
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type[Exception] = Exception,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time > self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info("circuit_breaker state=HALF_OPEN")
        return self._state

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        if self.state == CircuitState.OPEN:
            raise RuntimeError("Circuit breaker OPEN — downstream unavailable")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as exc:
            self._on_failure()
            raise exc

    def _on_success(self) -> None:
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.error(
                "circuit_breaker state=OPEN failures=%d", self._failure_count
            )


async def retry_with_backoff(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    **kwargs: Any,
) -> Any:
    """Retry с экспоненциальным откатом и jitter."""
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            if attempt == max_retries:
                logger.error("retry exhausted attempts=%d error=%s", attempt + 1, type(exc).__name__)
                raise
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(
                "retry attempt=%d delay=%.1fs error=%s", attempt + 1, delay, type(exc).__name__
            )
            await asyncio.sleep(delay)
