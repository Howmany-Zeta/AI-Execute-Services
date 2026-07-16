# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Per-backend rate limiting and circuit breaker guards (M-D.5 §3.11)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar, cast

from .constants import CircuitState
from .rate_limiter import CircuitBreaker, RateLimiter

T = TypeVar("T")


class BackendResilienceGuard:
    """Per-backend rate limit + circuit breaker — not shared across backends."""

    def __init__(
        self,
        backend_name: str,
        *,
        rate_limit_requests: int,
        rate_limit_window: int,
        circuit_breaker_threshold: int,
        circuit_breaker_timeout: int,
    ) -> None:
        self.backend_name = backend_name
        self.rate_limiter = RateLimiter(rate_limit_requests, rate_limit_window)
        self.circuit_breaker = CircuitBreaker(circuit_breaker_threshold, circuit_breaker_timeout)

    def is_circuit_open(self) -> bool:
        """Return True when the backend circuit breaker is OPEN."""
        return self.circuit_breaker.state == CircuitState.OPEN

    def execute(self, fn: Callable[[], T]) -> T:
        """Acquire rate token, run ``fn`` under breaker protection."""
        self.rate_limiter.acquire()
        return cast(T, self.circuit_breaker.call(fn))

    def get_remaining_quota(self) -> int:
        return self.rate_limiter.get_remaining_quota()

    def get_circuit_state(self) -> str:
        return self.circuit_breaker.get_state()
