"""P1-03: GroundingRouter chain walk and fail-open."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aiecs.tools.search_tool.backends.google_cse import GoogleCseBackend
from aiecs.tools.search_tool.backends.gemini_grounding import GeminiGroundingBackend
from aiecs.tools.search_tool.backends.grok_grounding import GrokGroundingBackend
from aiecs.tools.search_tool.backends.protocol import SearchCallParams
from aiecs.tools.search_tool.backends.registry import GroundingBackendRegistry
from aiecs.tools.search_tool.constants import AuthenticationError
from aiecs.tools.search_tool.core import SearchTool
from aiecs.tools.search_tool.router import GroundingRouter
from test.unit.tools.search_tool.fakes import FakeGroundingBackend


def _cse_config(**overrides: object) -> SearchTool.Config:
    base = {
        "google_api_key": "test-api-key",
        "google_cse_id": "test-cse-id",
        "grounding_provider": "auto",
        "grounding_provider_chain": "gemini,grok,google_cse",
        "rate_limit_requests": 100,
        "rate_limit_window": 86400,
        "circuit_breaker_threshold": 5,
        "circuit_breaker_timeout": 60,
    }
    base.update(overrides)
    return SearchTool.Config.model_construct(**base)


def _build_registry(config: SearchTool.Config) -> GroundingBackendRegistry:
    registry = GroundingBackendRegistry()
    registry.register(GeminiGroundingBackend(config))
    registry.register(GrokGroundingBackend(config))
    registry.register(GoogleCseBackend(config))
    return registry


@pytest.mark.gate_p1
def test_auto_chain_skips_unconfigured_gemini_grok_and_uses_cse() -> None:
    config = _cse_config()
    registry = _build_registry(config)
    router = GroundingRouter(registry, config)

    mock_service = MagicMock()
    mock_list = MagicMock()
    mock_list.execute.return_value = {
        "items": [
            {
                "title": "Result",
                "link": "https://example.com",
                "snippet": "snippet",
                "displayLink": "example.com",
            }
        ]
    }
    mock_service.cse.return_value.list.return_value = mock_list
    cse = registry.get("google_cse")
    assert cse is not None
    cse.service = mock_service  # type: ignore[attr-defined]

    params = SearchCallParams(query="test query", original_query="test query", num_results=5)
    raw, metadata = router.search_with_chain(params)

    assert raw.success is True
    assert metadata.backend_used == "google_cse"
    assert {"backend": "gemini", "reason": "not_configured"} in metadata.provider_chain_skipped
    assert {"backend": "grok", "reason": "not_configured"} in metadata.provider_chain_skipped
    assert metadata.provider_chain_attempted == ["gemini", "grok", "google_cse"]


@pytest.mark.gate_p1
def test_fake_gemini_failure_fail_open_preserves_cse_filters() -> None:
    config = _cse_config()
    registry = GroundingBackendRegistry()
    registry.register(
        FakeGroundingBackend("gemini", configured=True, succeed=False, error="timeout", error_type="timeout")
    )
    registry.register(GrokGroundingBackend(config))
    cse = GoogleCseBackend(config)
    registry.register(cse)
    router = GroundingRouter(registry, config)

    mock_service = MagicMock()
    mock_list = MagicMock()
    mock_list.execute.return_value = {"items": []}
    mock_service.cse.return_value.list.return_value = mock_list
    cse.service = mock_service

    params = SearchCallParams(
        query="annual report",
        original_query="annual report",
        num_results=5,
        date_restrict="m3",
        file_type="pdf",
    )
    raw, metadata = router.search_with_chain(params)

    assert raw.success is True
    assert metadata.backend_used == "google_cse"
    assert metadata.provider_chain_failed[0]["backend"] == "gemini"

    call_kwargs = mock_service.cse.return_value.list.call_args.kwargs
    assert call_kwargs["dateRestrict"] == "m3"
    assert call_kwargs["fileType"] == "pdf"


@pytest.mark.gate_p1
def test_forced_google_provider_uses_google_cse() -> None:
    config = _cse_config(grounding_provider="google")
    registry = _build_registry(config)
    router = GroundingRouter(registry, config)

    mock_service = MagicMock()
    mock_list = MagicMock()
    mock_list.execute.return_value = {"items": []}
    mock_service.cse.return_value.list.return_value = mock_list
    cse = registry.get("google_cse")
    assert cse is not None
    cse.service = mock_service  # type: ignore[attr-defined]

    params = SearchCallParams(query="q", original_query="q", num_results=3)
    raw, metadata = router.search_with_chain(params)

    assert raw.success is True
    assert metadata.backend_used == "google_cse"
    assert metadata.forced_provider == "google_cse"
    assert metadata.provider_chain_attempted == ["google_cse"]


@pytest.mark.gate_p1
def test_forced_gemini_not_configured_raises_authentication_error() -> None:
    config = _cse_config(grounding_provider="gemini")
    registry = _build_registry(config)
    router = GroundingRouter(registry, config)

    params = SearchCallParams(query="q", original_query="q", num_results=3)
    with pytest.raises(AuthenticationError, match="grounding_provider=gemini"):
        router.search_with_chain(params)


@pytest.mark.gate_p1
def test_router_skips_open_circuit_backend() -> None:
    config = _cse_config()
    registry = GroundingBackendRegistry()
    failing_gemini = FakeGroundingBackend(
        "gemini",
        configured=True,
        succeed=False,
        error="fail",
        error_type="search_api_error",
    )
    registry.register(failing_gemini)
    registry.register(GrokGroundingBackend(config))
    cse = GoogleCseBackend(config)
    registry.register(cse)
    router = GroundingRouter(registry, config)

    for _ in range(5):
        failing_gemini.search(SearchCallParams(query="q", original_query="q", num_results=1))

    assert failing_gemini.resilience.is_circuit_open() is True

    mock_service = MagicMock()
    mock_list = MagicMock()
    mock_list.execute.return_value = {"items": []}
    mock_service.cse.return_value.list.return_value = mock_list
    cse.service = mock_service

    params = SearchCallParams(query="q", original_query="q", num_results=3)
    raw, metadata = router.search_with_chain(params)

    assert raw.success is True
    assert metadata.backend_used == "google_cse"
    assert {"backend": "gemini", "reason": "circuit_open"} in metadata.provider_chain_skipped
