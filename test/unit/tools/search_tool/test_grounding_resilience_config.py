"""Grounding resilience Config fields + factory (§3.11)."""

from __future__ import annotations

import pytest

from aiecs.tools.search_tool.backends._resilience_factory import build_grounding_resilience_guard
from aiecs.tools.search_tool.core import SearchTool


@pytest.mark.gate_p1
def test_config_declares_grounding_rate_limit_fields() -> None:
    cfg = SearchTool.Config()
    assert cfg.grounding_rate_limit_requests == 60
    assert cfg.grounding_rate_limit_window == 3600
    assert cfg.grounding_circuit_breaker_threshold == 5
    assert cfg.grounding_circuit_breaker_timeout == 60
    # CSE defaults remain separate.
    assert cfg.rate_limit_requests == 100
    assert cfg.rate_limit_window == 86400


@pytest.mark.gate_p1
def test_factory_uses_grounding_config_fields() -> None:
    cfg = SearchTool.Config.model_construct(
        grounding_rate_limit_requests=12,
        grounding_rate_limit_window=120,
        grounding_circuit_breaker_threshold=3,
        grounding_circuit_breaker_timeout=15,
    )
    guard = build_grounding_resilience_guard("gemini", cfg)
    assert guard.rate_limiter.max_requests == 12
    assert guard.rate_limiter.time_window == 120
    assert guard.circuit_breaker.failure_threshold == 3
    assert guard.circuit_breaker.timeout == 15


@pytest.mark.gate_p1
def test_factory_per_backend_override_beats_grounding_default() -> None:
    cfg = SearchTool.Config.model_construct(
        grounding_rate_limit_requests=60,
        grounding_circuit_breaker_threshold=5,
        gemini_rate_limit_requests=7,
        gemini_circuit_breaker_threshold=2,
    )

    gemini = build_grounding_resilience_guard("gemini", cfg)
    grok = build_grounding_resilience_guard("grok", cfg)

    assert gemini.rate_limiter.max_requests == 7
    assert gemini.circuit_breaker.failure_threshold == 2
    assert grok.rate_limiter.max_requests == 60
    assert grok.circuit_breaker.failure_threshold == 5


@pytest.mark.gate_p1
def test_search_tool_wires_grounding_guards_from_config() -> None:
    tool = SearchTool(
        config={
            "grounding_rate_limit_requests": 9,
            "grounding_rate_limit_window": 99,
            "enable_intent_analysis": False,
            "enable_intelligent_cache": False,
            "enable_quality_analysis": False,
            "enable_context_tracking": False,
            "enable_deduplication": False,
        }
    )
    gemini = tool._registry.get("gemini")
    assert gemini is not None
    assert gemini.resilience.rate_limiter.max_requests == 9
    assert gemini.resilience.rate_limiter.time_window == 99
    # CSE keeps its own defaults.
    assert tool._google_cse_backend.resilience.rate_limiter.max_requests == tool.config.rate_limit_requests
