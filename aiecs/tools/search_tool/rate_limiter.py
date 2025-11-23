"""
Rate Limiting and Circuit Breaker Components

This module implements rate limiting using token bucket algorithm and
circuit breaker pattern for API resilience.
"""

import time
from collections import deque
from threading import Lock
from typing import Optional

from .constants import CircuitState, RateLimitError, CircuitBreakerOpenError


# ============================================================================
# Rate Limiter
# ============================================================================


class RateLimiter:
    """
    Token bucket rate limiter for API requests.

    Implements a token bucket algorithm to limit the rate of API requests
    and prevent quota exhaustion.
    """

    def __init__(self, max_requests: int, time_window: int):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.tokens = max_requests
        self.last_update = time.time()
        self.lock = Lock()
        self.request_history: deque = deque()

    def _refill_tokens(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        time_passed = now - self.last_update

        # Refill tokens proportionally to time passed
        refill_rate = self.max_requests / self.time_window
        tokens_to_add = time_passed * refill_rate

        self.tokens = min(self.max_requests, self.tokens + tokens_to_add)
        self.last_update = now

    def acquire(self, tokens: int = 1) -> bool:
        """
        Attempt to acquire tokens.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens acquired, False otherwise

        Raises:
            RateLimitError: If rate limit is exceeded
        """
        with self.lock:
            self._refill_tokens()

            # Clean up old request history
            cutoff_time = time.time() - self.time_window
            while self.request_history and self.request_history[0] < cutoff_time:
                self.request_history.popleft()

            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                self.request_history.append(time.time())
                return True
            else:
                # Calculate wait time
                wait_time = (tokens - self.tokens) / (self.max_requests / self.time_window)
                raise RateLimitError(f"Rate limit exceeded. {len(self.request_history)} requests in last " f"{self.time_window}s. Wait {wait_time:.1f}s before retrying.")

    def get_remaining_quota(self) -> int:
        """Get remaining quota"""
        with self.lock:
            self._refill_tokens()
            return int(self.tokens)


# ============================================================================
# Circuit Breaker
# ============================================================================


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for API resilience.

    Implements a circuit breaker to prevent cascading failures when
    the API is experiencing issues.
    """

    def __init__(self, failure_threshold: int, timeout: int):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Timeout in seconds before trying half-open state
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        self.lock = Lock()

    def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        with self.lock:
            if self.state == CircuitState.OPEN:
                # Check if timeout has passed
                if time.time() - self.last_failure_time >= self.timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.failure_count = 0
                else:
                    raise CircuitBreakerOpenError(f"Circuit breaker is OPEN. Retry after " f"{self.timeout - (time.time() - self.last_failure_time):.1f}s")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful call"""
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed call"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN

    def get_state(self) -> str:
        """Get current circuit state"""
        return self.state.value
