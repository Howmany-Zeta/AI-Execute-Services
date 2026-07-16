"""P1-04: Search error policy and failure envelopes (M-D.5 §3.10)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aiecs.tools.search_tool.backends.gemini_grounding import GeminiGroundingBackend
from aiecs.tools.search_tool.backends.grok_grounding import GrokGroundingBackend
from aiecs.tools.search_tool.backends.protocol import SearchCallParams
from aiecs.tools.search_tool.backends.registry import GroundingBackendRegistry
from aiecs.tools.search_tool.constants import RateLimitError, SearchAPIError, ValidationError
from aiecs.tools.search_tool.core import SearchTool
from aiecs.tools.search_tool.errors import is_cse_only_deployment
from aiecs.tools.search_tool.resilience import BackendResilienceGuard
from test.unit.tools.search_tool.fakes import FakeGroundingBackend


def _exhausted_rate_guard(name: str) -> BackendResilienceGuard:
    """Guard whose single token is already spent → next execute() raises RateLimitError."""
    guard = BackendResilienceGuard(
        name,
        rate_limit_requests=1,
        rate_limit_window=3600,
        circuit_breaker_threshold=5,
        circuit_breaker_timeout=60,
    )
    guard.rate_limiter.acquire()
    return guard


def _cse_config(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "google_api_key": "test-api-key",
        "google_cse_id": "test-cse-id",
        "grounding_provider": "google_cse",
        "enable_intent_analysis": False,
        "enable_context_tracking": False,
        "enable_intelligent_cache": False,
        "retry_attempts": 1,
    }
    base.update(overrides)
    return base


@pytest.mark.gate_p1
def test_empty_query_raises_validation_error() -> None:
    tool = SearchTool(config=_cse_config())
    with pytest.raises(ValidationError, match="Query cannot be empty"):
        tool.search_web("", auto_enhance=False)


@pytest.mark.gate_p1
def test_cse_only_api_fail_auto_raises_search_api_error() -> None:
    mock_service = MagicMock()
    mock_list = MagicMock()
    mock_list.execute.side_effect = RuntimeError("simulated CSE API failure")
    mock_service.cse.return_value.list.return_value = mock_list

    tool = SearchTool(config=_cse_config(search_error_mode="auto"))
    tool.service = mock_service

    with pytest.raises(SearchAPIError):
        tool.search_web("test query", auto_enhance=False)


@pytest.mark.gate_p1
def test_auto_chain_all_fake_backends_fail_returns_dict() -> None:
    config = _cse_config(
        grounding_provider="auto",
        grounding_provider_chain="gemini,grok,google_cse",
        gemini_api_key="test-gemini-key",
        grok_api_key="test-grok-key",
    )
    tool = SearchTool(config=config)

    registry = GroundingBackendRegistry()
    registry.register(
        FakeGroundingBackend("gemini", configured=True, succeed=False, error="gemini down")
    )
    registry.register(
        FakeGroundingBackend("grok", configured=True, succeed=False, error="grok down")
    )
    registry.register(
        FakeGroundingBackend("google_cse", configured=True, succeed=False, error="cse down")
    )
    tool._registry = registry

    result = tool.search_web("test query", auto_enhance=False)

    assert result["success"] is False
    assert result["results"] == []
    assert "_error" in result
    assert result["_search_metadata"]["routing_outcome"] == "all_backends_exhausted"
    assert len(result["_search_metadata"]["provider_chain_failed"]) == 3


@pytest.mark.gate_p1
def test_return_dict_mode_cse_only_fail_returns_dict() -> None:
    mock_service = MagicMock()
    mock_list = MagicMock()
    mock_list.execute.side_effect = RuntimeError("simulated CSE API failure")
    mock_service.cse.return_value.list.return_value = mock_list

    tool = SearchTool(config=_cse_config(search_error_mode="return_dict"))
    tool.service = mock_service

    result = tool.search_web("test query", auto_enhance=False)

    assert result["success"] is False
    assert result["results"] == []
    assert "_error" in result
    assert result["_search_metadata"]["search_error_mode"] == "return_dict"


@pytest.mark.gate_p1
def test_gemini_backend_rate_limit_maps_to_rate_limit_exceeded() -> None:
    """Built-in Gemini must type resilience RateLimitError like CSE (§3.10 / §3.11)."""
    cfg = SearchTool.Config.model_construct(
        gemini_grounding_auth="googleai",
        gemini_api_key="test-gemini-key",
    )
    backend = GeminiGroundingBackend(
        cfg,
        resilience=_exhausted_rate_guard("gemini"),
        client_factory=MagicMock(),
    )
    raw = backend.search(SearchCallParams(query="q", original_query="q", num_results=5))
    assert raw.success is False
    assert raw.error_type == "rate_limit_exceeded"
    assert raw.backend == "gemini"


@pytest.mark.gate_p1
def test_grok_backend_rate_limit_maps_to_rate_limit_exceeded() -> None:
    cfg = SearchTool.Config.model_construct(
        grok_grounding_auth="xai",
        grok_api_key="test-grok-key",
    )
    backend = GrokGroundingBackend(
        cfg,
        resilience=_exhausted_rate_guard("grok"),
        client_factory=MagicMock(),
    )
    raw = backend.search(SearchCallParams(query="q", original_query="q", num_results=5))
    assert raw.success is False
    assert raw.error_type == "rate_limit_exceeded"
    assert raw.backend == "grok"


@pytest.mark.gate_p1
def test_forced_gemini_rate_limit_raises_tier_a() -> None:
    """Forced gemini + local rate limit → RateLimitError (not Tier C dict)."""
    tool = SearchTool(
        config=_cse_config(
            grounding_provider="gemini",
            gemini_api_key="test-gemini-key",
            gemini_grounding_auth="googleai",
            search_error_mode="auto",
        )
    )
    gemini = GeminiGroundingBackend(
        tool.config,
        resilience=_exhausted_rate_guard("gemini"),
        client_factory=MagicMock(),
    )
    registry = GroundingBackendRegistry()
    registry.register(gemini)
    registry.register(FakeGroundingBackend("grok", configured=False))
    registry.register(FakeGroundingBackend("google_cse", configured=False))
    tool._registry = registry

    with pytest.raises(RateLimitError):
        tool.search_web("test query", auto_enhance=False, grounding_provider="gemini")


@pytest.mark.gate_p1
def test_is_cse_only_false_when_custom_backend_configured() -> None:
    """Custom Exa must not inherit CSE-only raise semantics (§3.10 / §8)."""
    cfg = SearchTool.Config.model_construct(
        grounding_provider="auto",
        grounding_provider_chain="exa,google_cse",
        google_api_key="cse-key",
        google_cse_id="cse-id",
    )
    # Credential-only check would incorrectly say CSE-only (no gemini/grok keys).
    assert is_cse_only_deployment(cfg) is False

    registry = GroundingBackendRegistry()
    registry.register(FakeGroundingBackend("exa", configured=True))
    registry.register(FakeGroundingBackend("google_cse", configured=True))
    assert is_cse_only_deployment(cfg, registry=registry) is False


@pytest.mark.gate_p1
def test_is_cse_only_true_without_grounding_or_custom() -> None:
    cfg = SearchTool.Config.model_construct(
        grounding_provider="auto",
        grounding_provider_chain="gemini,grok,google_cse",
        google_api_key="cse-key",
        google_cse_id="cse-id",
    )
    registry = GroundingBackendRegistry()
    registry.register(FakeGroundingBackend("gemini", configured=False))
    registry.register(FakeGroundingBackend("grok", configured=False))
    registry.register(FakeGroundingBackend("google_cse", configured=True))
    assert is_cse_only_deployment(cfg, registry=registry) is True


@pytest.mark.gate_p1
def test_auto_custom_exa_chain_exhaustion_returns_tier_c_not_raise() -> None:
    """exa + CSE failure must return Tier C dict (not CSE-only raise)."""
    tool = SearchTool(
        config=_cse_config(
            grounding_provider="auto",
            grounding_provider_chain="exa,google_cse",
            search_error_mode="auto",
        ),
        custom_grounding_backends=[
            FakeGroundingBackend("exa", succeed=False, error="exa down"),
        ],
    )
    tool._registry.register(
        FakeGroundingBackend("google_cse", succeed=False, error="cse down")
    )
    # Neutralize built-ins so only exa + cse participate.
    tool._registry.register(FakeGroundingBackend("gemini", configured=False))
    tool._registry.register(FakeGroundingBackend("grok", configured=False))

    result = tool.search_web("test query", auto_enhance=False)

    assert result["success"] is False
    assert "_error" in result
    assert result["_search_metadata"]["routing_outcome"] == "all_backends_exhausted"


@pytest.mark.gate_p1
def test_forced_grok_rate_limit_raises_tier_a() -> None:
    tool = SearchTool(
        config=_cse_config(
            grounding_provider="grok",
            grok_api_key="test-grok-key",
            grok_grounding_auth="xai",
            search_error_mode="auto",
        )
    )
    grok = GrokGroundingBackend(
        tool.config,
        resilience=_exhausted_rate_guard("grok"),
        client_factory=MagicMock(),
    )
    registry = GroundingBackendRegistry()
    registry.register(FakeGroundingBackend("gemini", configured=False))
    registry.register(grok)
    registry.register(FakeGroundingBackend("google_cse", configured=False))
    tool._registry = registry

    with pytest.raises(RateLimitError):
        tool.search_web("test query", auto_enhance=False, grounding_provider="grok")
