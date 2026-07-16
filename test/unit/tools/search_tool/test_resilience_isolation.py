"""P1-02: Per-backend resilience isolation (§3.11)."""

from __future__ import annotations

import pytest

from aiecs.tools.search_tool.constants import CircuitState, SearchAPIError
from aiecs.tools.search_tool.core import SearchTool
from aiecs.tools.search_tool.resilience import BackendResilienceGuard
from test.unit.tools.search_tool.fakes import FakeGroundingBackend


def _fail_request() -> None:
    raise SearchAPIError("simulated provider failure")


@pytest.mark.gate_p1
def test_gemini_guard_failures_do_not_open_cse_breaker() -> None:
    cse_guard = BackendResilienceGuard(
        "google_cse",
        rate_limit_requests=100,
        rate_limit_window=86400,
        circuit_breaker_threshold=5,
        circuit_breaker_timeout=60,
    )
    gemini_guard = BackendResilienceGuard(
        "gemini",
        rate_limit_requests=60,
        rate_limit_window=3600,
        circuit_breaker_threshold=5,
        circuit_breaker_timeout=60,
    )

    for _ in range(5):
        with pytest.raises(SearchAPIError):
            gemini_guard.execute(_fail_request)

    assert gemini_guard.is_circuit_open() is True
    assert gemini_guard.circuit_breaker.state == CircuitState.OPEN
    assert cse_guard.is_circuit_open() is False
    assert cse_guard.circuit_breaker.state == CircuitState.CLOSED


@pytest.mark.gate_p1
def test_cse_guard_trips_independently() -> None:
    cse_guard = BackendResilienceGuard(
        "google_cse",
        rate_limit_requests=100,
        rate_limit_window=86400,
        circuit_breaker_threshold=3,
        circuit_breaker_timeout=60,
    )
    gemini_guard = BackendResilienceGuard(
        "gemini",
        rate_limit_requests=60,
        rate_limit_window=3600,
        circuit_breaker_threshold=3,
        circuit_breaker_timeout=60,
    )

    for _ in range(3):
        with pytest.raises(SearchAPIError):
            cse_guard.execute(_fail_request)

    assert cse_guard.is_circuit_open() is True
    assert gemini_guard.is_circuit_open() is False


@pytest.mark.gate_p1
def test_get_quota_status_reports_per_backend_resilience() -> None:
    tool = SearchTool(
        config={
            "google_api_key": "cse-key",
            "google_cse_id": "cse-id",
            "enable_intent_analysis": False,
            "enable_intelligent_cache": False,
            "enable_quality_analysis": False,
            "enable_context_tracking": False,
            "enable_deduplication": False,
        }
    )
    gemini = FakeGroundingBackend("gemini", configured=True)
    for _ in range(5):
        with pytest.raises(SearchAPIError):
            gemini.resilience.execute(_fail_request)
    tool._registry.register(gemini)

    status = tool.get_quota_status()

    # CSE top-level fields preserved (backward compat).
    assert "remaining_quota" in status
    assert "circuit_breaker_state" in status
    assert status["circuit_breaker_state"] == "closed"

    resilience = status["resilience"]
    assert "google_cse" in resilience
    assert "gemini" in resilience
    assert "grok" in resilience
    assert resilience["gemini"]["circuit_state"] == "open"
    assert resilience["google_cse"]["circuit_state"] == "closed"
    assert isinstance(resilience["gemini"]["remaining_quota"], int)
    assert isinstance(resilience["grok"]["remaining_quota"], int)
