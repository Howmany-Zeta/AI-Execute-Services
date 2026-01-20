"""
Rate limiting and circuit breaker implementations for the scraper tool.
"""

import threading
import time
from typing import Any, Callable, Dict

from .constants import CircuitBreakerOpenError, CircuitState


class RateLimiter:
    """Token bucket rate limiter with per-domain tracking."""

    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.interval = 60.0 / requests_per_minute
        self._domains: Dict[str, float] = {}
        self._lock = threading.Lock()

    def acquire(self, domain: str) -> bool:
        """Try to acquire a token for the domain. Returns True if acquired."""
        with self._lock:
            now = time.time()
            last_request = self._domains.get(domain, 0)
            if now - last_request >= self.interval:
                self._domains[domain] = now
                return True
            return False

    def wait_time(self, domain: str) -> float:
        """Get remaining wait time in seconds for the domain."""
        with self._lock:
            now = time.time()
            last_request = self._domains.get(domain, 0)
            remaining = self.interval - (now - last_request)
            return max(0.0, remaining)


class AdaptiveRateLimiter(RateLimiter):
    """Rate limiter that adapts based on server responses."""

    def __init__(self, requests_per_minute: int = 30):
        super().__init__(requests_per_minute)
        self._max_rpm = requests_per_minute
        self._min_rpm = max(1, requests_per_minute // 10)
        self._domain_rpm: Dict[str, float] = {}

    def _get_interval(self, domain: str) -> float:
        rpm = self._domain_rpm.get(domain, self.requests_per_minute)
        return 60.0 / rpm

    def acquire(self, domain: str) -> bool:
        with self._lock:
            now = time.time()
            last_request = self._domains.get(domain, 0)
            interval = self._get_interval(domain)
            if now - last_request >= interval:
                self._domains[domain] = now
                return True
            return False

    def wait_time(self, domain: str) -> float:
        with self._lock:
            now = time.time()
            last_request = self._domains.get(domain, 0)
            interval = self._get_interval(domain)
            return max(0.0, interval - (now - last_request))

    def on_success(self, domain: str) -> None:
        """Slightly increase rate on success (up to max)."""
        with self._lock:
            current = self._domain_rpm.get(domain, self.requests_per_minute)
            self._domain_rpm[domain] = min(self._max_rpm, current * 1.1)

    def on_rate_limit(self, domain: str) -> None:
        """Significantly decrease rate on rate limit response."""
        with self._lock:
            current = self._domain_rpm.get(domain, self.requests_per_minute)
            self._domain_rpm[domain] = max(self._min_rpm, current * 0.5)

    def on_error(self, domain: str) -> None:
        """Slightly decrease rate on error."""
        with self._lock:
            current = self._domain_rpm.get(domain, self.requests_per_minute)
            self._domain_rpm[domain] = max(self._min_rpm, current * 0.9)


class CircuitBreaker:
    """Circuit breaker pattern implementation."""

    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._last_failure_time: float = 0
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        """Check if circuit is closed or half-open (allowing requests)."""
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            if self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time >= self.reset_timeout:
                    self._state = CircuitState.HALF_OPEN
                    return True
                return False
            return True  # HALF_OPEN

    def record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            self._failures = 0
            self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed call."""
        with self._lock:
            self._failures += 1
            self._last_failure_time = time.time()
            if self._failures >= self.failure_threshold:
                self._state = CircuitState.OPEN

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute function with circuit breaker protection."""
        if not self.is_available():
            raise CircuitBreakerOpenError("Circuit breaker is open")
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise

    async def call_async(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute async function with circuit breaker protection."""
        if not self.is_available():
            raise CircuitBreakerOpenError("Circuit breaker is open")
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise


class DomainCircuitBreaker:
    """Manages per-domain circuit breakers."""

    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()

    def get_breaker(self, domain: str) -> CircuitBreaker:
        """Get or create a circuit breaker for the domain."""
        with self._lock:
            if domain not in self._breakers:
                self._breakers[domain] = CircuitBreaker(
                    self.failure_threshold, self.reset_timeout
                )
            return self._breakers[domain]

    def is_domain_available(self, domain: str) -> bool:
        """Check if the domain's circuit breaker allows requests."""
        return self.get_breaker(domain).is_available()

