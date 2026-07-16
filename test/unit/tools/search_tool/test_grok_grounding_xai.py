"""P3-01: GrokGroundingBackend xAI sync OpenAI path."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from openai import APIStatusError, AuthenticationError

from aiecs.tools.search_tool.backends.grok_grounding import GrokGroundingBackend, XAI_BASE_URL
from aiecs.tools.search_tool.backends.protocol import SearchCallParams
from aiecs.tools.search_tool.backends.registry import GroundingBackendRegistry
from aiecs.tools.search_tool.constants import ValidationError
from aiecs.tools.search_tool.core import SearchTool
from test.unit.tools.search_tool.fakes import FakeGroundingBackend


def _xai_config(**overrides: object) -> SearchTool.Config:
    base = {
        "grok_grounding_auth": "xai",
        "grok_api_key": "test-grok-key",
        "grounding_model_grok": "grok-4.5",
        "grounding_timeout_seconds": 30.0,
        "rate_limit_requests": 100,
        "rate_limit_window": 86400,
        "circuit_breaker_threshold": 5,
        "circuit_breaker_timeout": 60,
    }
    base.update(overrides)
    return SearchTool.Config.model_construct(**base)


def _params(**overrides: object) -> SearchCallParams:
    base: dict[str, object] = {
        "query": "What is xAI?",
        "original_query": "What is xAI?",
        "num_results": 5,
    }
    base.update(overrides)
    return SearchCallParams(**base)  # type: ignore[arg-type]


def _mock_response(*, citations: list[str], text: str = "grounded answer") -> MagicMock:
    response = MagicMock()
    response.output_text = text
    response.citations = citations
    response.output = []
    return response


def _api_status_error(status_code: int, message: str) -> APIStatusError:
    request = MagicMock()
    response = MagicMock()
    response.status_code = status_code
    response.headers = {}
    return APIStatusError(message, response=response, body={"error": {"message": message}})


@pytest.mark.gate_p3
def test_xai_citations_success() -> None:
    mock_client = MagicMock()
    mock_client.responses.create.return_value = _mock_response(
        citations=["https://x.ai/news", "https://docs.x.ai/developers/release-notes"],
    )
    factory = MagicMock(return_value=mock_client)
    backend = GrokGroundingBackend(_xai_config(), client_factory=factory)

    result = backend.search(_params(date_restrict="m3"))

    assert result.success is True
    assert len(result.citations) == 2
    assert result.citations[0]["url"] == "https://x.ai/news"
    assert result.answer == "grounded answer"
    assert result.provider_native == {
        "grok_auth_mode": "xai",
        "grok_client_mode": "sync_openai",
        "grok_maas_web_search_capable": None,
    }
    assert "date_restrict" in result.params_ignored
    factory.assert_called_once_with(
        api_key="test-grok-key",
        base_url=XAI_BASE_URL,
        timeout=30.0,
    )
    call_kwargs = mock_client.responses.create.call_args.kwargs
    assert call_kwargs["model"] == "grok-4.5"
    assert call_kwargs["tools"] == [{"type": "web_search"}]


@pytest.mark.gate_p3
def test_xai_503_returns_structured_fail() -> None:
    mock_client = MagicMock()
    mock_client.responses.create.side_effect = _api_status_error(503, "service unavailable")
    backend = GrokGroundingBackend(
        _xai_config(),
        client_factory=MagicMock(return_value=mock_client),
    )

    result = backend.search(_params())

    assert result.success is False
    assert result.error_type == "http_503"


@pytest.mark.gate_p3
def test_xai_401_returns_auth_failure() -> None:
    mock_client = MagicMock()
    mock_client.responses.create.side_effect = AuthenticationError(
        "invalid api key",
        response=MagicMock(status_code=401, headers={}),
        body={"error": {"message": "invalid api key"}},
    )
    backend = GrokGroundingBackend(
        _xai_config(),
        client_factory=MagicMock(return_value=mock_client),
    )

    result = backend.search(_params())

    assert result.success is False
    assert result.error_type == "auth"


@pytest.mark.gate_p3
def test_xai_empty_citations_returns_structured_fail() -> None:
    mock_client = MagicMock()
    mock_client.responses.create.return_value = _mock_response(citations=[], text="no sources")
    backend = GrokGroundingBackend(
        _xai_config(),
        client_factory=MagicMock(return_value=mock_client),
    )

    result = backend.search(_params())

    assert result.success is False
    assert result.error_type == "empty_citations"


@pytest.mark.gate_p3
def test_domain_filters_mutual_exclusion_raises_validation_error() -> None:
    backend = GrokGroundingBackend(_xai_config(), client_factory=MagicMock())
    with pytest.raises(ValidationError, match="mutually exclusive"):
        backend.search(
            _params(
                allowed_domains=["a.com"],
                blocked_domains=["b.com"],
            )
        )


@pytest.mark.gate_p3
def test_domain_filters_max_five_raises_validation_error() -> None:
    backend = GrokGroundingBackend(_xai_config(), client_factory=MagicMock())
    with pytest.raises(ValidationError, match="at most 5"):
        backend.search(_params(allowed_domains=[f"d{i}.com" for i in range(6)]))


@pytest.mark.gate_p3
def test_allowed_domains_passed_to_web_search_tool() -> None:
    mock_client = MagicMock()
    mock_client.responses.create.return_value = _mock_response(citations=["https://a.com/1"])
    backend = GrokGroundingBackend(
        _xai_config(),
        client_factory=MagicMock(return_value=mock_client),
    )

    result = backend.search(_params(allowed_domains=["a.com", "b.com"]))

    assert result.success is True
    tools = mock_client.responses.create.call_args.kwargs["tools"]
    assert tools[0]["filters"]["allowed_domains"] == ["a.com", "b.com"]
    assert "allowed_domains" in result.params_applied


@pytest.mark.gate_p3
def test_search_web_completes_synchronously_no_event_loop() -> None:
    mock_client = MagicMock()
    mock_client.responses.create.return_value = _mock_response(
        citations=["https://x.ai/company"],
        text="xAI company overview",
    )
    tool = SearchTool(
        config={
            "grok_api_key": "test-grok-key",
            "grounding_provider": "grok",
            "enable_intent_analysis": False,
            "enable_context_tracking": False,
            "enable_intelligent_cache": False,
            "enable_quality_analysis": False,
        }
    )
    live = GrokGroundingBackend(tool.config, client_factory=MagicMock(return_value=mock_client))
    registry = GroundingBackendRegistry()
    registry.register(FakeGroundingBackend("gemini", configured=False))
    registry.register(live)
    registry.register(FakeGroundingBackend("google_cse", configured=False))
    tool._registry = registry

    # Must not require a running event loop
    with pytest.raises(RuntimeError):
        asyncio.get_running_loop()

    result = tool.search_web("What is xAI?", auto_enhance=False)

    assert result["_search_metadata"]["backend_used"] == "grok"
    assert result["_search_metadata"]["grok_auth_mode"] == "xai"
    assert result["_search_metadata"]["grok_client_mode"] == "sync_openai"
    assert result["results"]
    assert result["grounding_answer"] == "xAI company overview"
