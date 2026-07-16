"""P1-05: search_batch backend pinning and P95 budget (M-D.5 §3.7)."""

from __future__ import annotations

import pytest

from aiecs.tools.search_tool.backends.registry import GroundingBackendRegistry
from aiecs.tools.search_tool.constants import CircuitBreakerOpenError, RateLimitError
from aiecs.tools.search_tool.core import SearchTool
from aiecs.tools.search_tool.router import BatchRoutingContext
from test.unit.tools.search_tool.fakes import FakeGroundingBackend


def _batch_config(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "grounding_provider": "auto",
        "grounding_provider_chain": "gemini,grok,google_cse",
        "batch_routing_mode": "pin_on_first_success",
        "batch_p95_budget_seconds": 15.0,
        "grounding_timeout_seconds": 30.0,
        "enable_intent_analysis": False,
        "enable_context_tracking": False,
        "enable_intelligent_cache": False,
        "enable_quality_analysis": False,
        "enable_deduplication": False,
        "max_batch_queries": 3,
    }
    base.update(overrides)
    return base


def _tool_with_fakes(
    *,
    gemini: FakeGroundingBackend,
    grok: FakeGroundingBackend,
    cse: FakeGroundingBackend,
    **config_overrides: object,
) -> SearchTool:
    tool = SearchTool(config=_batch_config(**config_overrides))
    registry = GroundingBackendRegistry()
    registry.register(gemini)
    registry.register(grok)
    registry.register(cse)
    tool._registry = registry
    return tool


@pytest.mark.gate_p1
def test_pin_on_first_success_chain_walks_once_gemini_not_recalled() -> None:
    gemini = FakeGroundingBackend("gemini", succeed=False, error="gemini down")
    grok = FakeGroundingBackend("grok", succeed=False, error="grok down")
    cse = FakeGroundingBackend(
        "google_cse",
        citations=[{"url": "https://cse.example/1", "title": "CSE", "snippet": "ok", "domain": "cse.example"}],
    )
    tool = _tool_with_fakes(gemini=gemini, grok=grok, cse=cse)

    result = tool.search_batch(
        queries=["q1 about alpha", "q2 about beta", "q3 about gamma"],
        num_results=3,
        auto_enhance=False,
    )

    assert result["_metadata"]["batch_routing_mode"] == "pin_on_first_success"
    assert result["_metadata"]["batch_pinned_backend"] == "google_cse"
    assert result["_metadata"]["batch_first_query_chain_attempted"] == ["gemini", "grok", "google_cse"]
    assert result["_metadata"]["per_query_backend_used"] == ["google_cse", "google_cse", "google_cse"]
    assert len(gemini.search_calls) == 1
    assert len(grok.search_calls) == 1
    assert len(cse.search_calls) == 3
    assert all(bucket.get("success") is not False for bucket in result["per_query"])
    assert result["per_query"][1]["_search_metadata"]["batch_used_pinned_backend"] is True
    assert result["per_query"][2]["_search_metadata"]["batch_used_pinned_backend"] is True


@pytest.mark.gate_p1
def test_batch_p95_budget_seconds_caps_per_query_timeout() -> None:
    gemini = FakeGroundingBackend("gemini", succeed=True)
    grok = FakeGroundingBackend("grok", succeed=True)
    cse = FakeGroundingBackend("google_cse", succeed=True)
    tool = _tool_with_fakes(
        gemini=gemini,
        grok=grok,
        cse=cse,
        batch_p95_budget_seconds=15.0,
        grounding_timeout_seconds=30.0,
    )

    result = tool.search_batch(
        queries=["q1", "q2", "q3"],
        num_results=2,
        auto_enhance=False,
    )

    assert result["_metadata"]["batch_p95_budget_seconds"] == 15.0
    assert result["_metadata"]["batch_elapsed_ms"] / 1000.0 <= 15.0 + 1.0
    # Q1 timeout = min(30, 15/3) ≈ 5.0
    assert gemini.search_calls[0].timeout_seconds == pytest.approx(5.0, abs=0.05)
    # Q2/Q3 use pinned gemini; remaining budget still ~15s → min(30, ~15/2) ≈ 7.5
    assert gemini.search_calls[1].timeout_seconds <= 30.0
    assert gemini.search_calls[1].timeout_seconds == pytest.approx(7.5, abs=0.5)


@pytest.mark.gate_p1
def test_per_query_mode_independent_chain_walks_no_pin() -> None:
    gemini = FakeGroundingBackend("gemini", succeed=False, error="gemini down")
    grok = FakeGroundingBackend("grok", succeed=False, error="grok down")
    cse = FakeGroundingBackend("google_cse", succeed=True)
    tool = _tool_with_fakes(
        gemini=gemini,
        grok=grok,
        cse=cse,
        batch_routing_mode="per_query",
    )

    result = tool.search_batch(
        queries=["q1", "q2", "q3"],
        num_results=2,
        auto_enhance=False,
        batch_routing_mode="per_query",
    )

    assert result["_metadata"]["batch_pinned_backend"] is None
    assert result["_metadata"]["batch_routing_mode"] == "per_query"
    assert result["_metadata"]["per_query_backend_used"] == ["google_cse", "google_cse", "google_cse"]
    assert len(gemini.search_calls) == 3
    assert len(grok.search_calls) == 3
    assert len(cse.search_calls) == 3


@pytest.mark.gate_p1
def test_partial_tier_c_q2_fails_q1_q3_ok() -> None:
    # Q1 pins gemini; Q2 gemini fails and chain_tail (grok, cse) also fail; Q3 gemini ok again
    gemini = FakeGroundingBackend(
        "gemini",
        succeed_sequence=[True, False, True],
        citations=[{"url": "https://g.example/1", "title": "G", "snippet": "ok", "domain": "g.example"}],
    )
    grok = FakeGroundingBackend("grok", succeed=False, error="grok down")
    cse = FakeGroundingBackend("google_cse", succeed=False, error="cse down")
    tool = _tool_with_fakes(gemini=gemini, grok=grok, cse=cse)

    result = tool.search_batch(
        queries=["q1", "q2", "q3"],
        num_results=2,
        auto_enhance=False,
    )

    assert result["_metadata"]["batch_pinned_backend"] == "gemini"
    assert result["_metadata"]["batch_partial_failure"] is True
    assert result["_metadata"]["failed_query_indices"] == [1]
    assert result["per_query"][0].get("success") is not False
    assert result["per_query"][0]["results"]
    assert result["per_query"][1]["success"] is False
    assert result["per_query"][1]["results"] == []
    assert result["per_query"][2].get("success") is not False
    assert result["per_query"][2]["results"]
    # Pin unchanged: Q3 still hits gemini (not full chain re-walk from head for skip)
    assert len(gemini.search_calls) == 3
    # Q2 fail-open tried chain_tail after pinned gemini failed
    assert len(grok.search_calls) == 1
    assert len(cse.search_calls) == 1


@pytest.mark.gate_p1
def test_batch_rate_limit_raises_tier_a_aborts_batch() -> None:
    """Per-query rate_limit_exceeded must raise (not Tier C bucket) — §3.10."""
    cse = FakeGroundingBackend(
        "google_cse",
        succeed=False,
        error="CSE rate limited",
        error_type="rate_limit_exceeded",
    )
    tool = _tool_with_fakes(
        gemini=FakeGroundingBackend("gemini", configured=False),
        grok=FakeGroundingBackend("grok", configured=False),
        cse=cse,
        grounding_provider="google_cse",
    )

    with pytest.raises(RateLimitError):
        tool.search_batch(
            queries=["q1", "q2"],
            num_results=2,
            auto_enhance=False,
            grounding_provider="google_cse",
        )

    # Batch aborted on first query — second query never dispatched.
    assert len(cse.search_calls) == 1


@pytest.mark.gate_p1
def test_batch_circuit_open_raises_tier_a_aborts_batch() -> None:
    cse = FakeGroundingBackend(
        "google_cse",
        succeed=False,
        error="CSE circuit open",
        error_type="circuit_open",
    )
    tool = _tool_with_fakes(
        gemini=FakeGroundingBackend("gemini", configured=False),
        grok=FakeGroundingBackend("grok", configured=False),
        cse=cse,
        grounding_provider="google_cse",
    )

    with pytest.raises(CircuitBreakerOpenError):
        tool.search_batch(
            queries=["q1", "q2"],
            num_results=2,
            auto_enhance=False,
            grounding_provider="google_cse",
        )

    assert len(cse.search_calls) == 1


@pytest.mark.gate_p1
def test_batch_routing_context_deadline_and_timeout_math() -> None:
    ctx = BatchRoutingContext(mode="pin_on_first_success", budget_seconds=15.0)
    ctx.start_deadline(now=100.0)
    assert ctx.deadline == 115.0
    assert ctx.remaining_seconds(now=100.0) == 15.0
    assert ctx.per_query_timeout(3, grounding_timeout_seconds=30.0, now=100.0) == 5.0
    assert ctx.remaining_seconds(now=110.0) == 5.0
    assert ctx.per_query_timeout(2, grounding_timeout_seconds=30.0, now=110.0) == pytest.approx(2.5)
