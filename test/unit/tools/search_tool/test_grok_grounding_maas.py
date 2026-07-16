"""P3-02: GrokGroundingBackend Vertex MaaS gate + sync token path."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aiecs.tools.search_tool.backends.credentials import build_maas_openapi_base_url
from aiecs.tools.search_tool.backends.grok_grounding import GrokGroundingBackend
from aiecs.tools.search_tool.backends.protocol import SearchCallParams
from aiecs.tools.search_tool.core import SearchTool


def _maas_config(**overrides: object) -> SearchTool.Config:
    base = {
        "grok_grounding_auth": "auto",
        "grok_maas_web_search_enabled": False,
        "vertex_project_id_maas": "maas-proj",
        "vertex_location_maas": "global",
        "google_application_credentials_vertex_maas": "/tmp/fake-maas.json",
        "grounding_model_grok": "grok-4.5",
        "grounding_timeout_seconds": 30.0,
        "grok_maas_capability_probe": False,
        "maas_capability_probe_ttl_seconds": 3600,
        "rate_limit_requests": 100,
        "rate_limit_window": 86400,
        "circuit_breaker_threshold": 5,
        "circuit_breaker_timeout": 60,
    }
    base.update(overrides)
    return SearchTool.Config.model_construct(**base)


def _params(**overrides: object) -> SearchCallParams:
    base: dict[str, object] = {
        "query": "What is Vertex MaaS Grok?",
        "original_query": "What is Vertex MaaS Grok?",
        "num_results": 5,
    }
    base.update(overrides)
    return SearchCallParams(**base)  # type: ignore[arg-type]


def _mock_response(*, citations: list[str], text: str = "maas grounded") -> MagicMock:
    response = MagicMock()
    response.output_text = text
    response.citations = citations
    response.output = []
    return response


@pytest.mark.gate_p3
def test_maas_only_flag_false_skips_grok_no_http() -> None:
    factory = MagicMock()
    token_provider = MagicMock()
    backend = GrokGroundingBackend(
        _maas_config(grok_maas_web_search_enabled=False, grok_grounding_auth="auto"),
        client_factory=factory,
        maas_token_provider=token_provider,
    )

    assert backend.auth_mode is None
    assert backend.is_configured() is False
    factory.assert_not_called()
    token_provider.get_access_token.assert_not_called()


@pytest.mark.gate_p3
def test_xai_wins_over_maas_in_auto() -> None:
    mock_client = MagicMock()
    mock_client.responses.create.return_value = _mock_response(
        citations=["https://x.ai/news"],
    )
    factory = MagicMock(return_value=mock_client)
    token_provider = MagicMock()
    backend = GrokGroundingBackend(
        _maas_config(
            grok_grounding_auth="auto",
            grok_api_key="xai-key",
            grok_maas_web_search_enabled=True,
        ),
        client_factory=factory,
        maas_token_provider=token_provider,
    )

    assert backend.auth_mode == "xai"
    assert backend.is_configured() is True
    result = backend.search(_params())

    assert result.success is True
    assert result.provider_native["grok_auth_mode"] == "xai"
    token_provider.get_access_token.assert_not_called()
    factory.assert_called_once()
    assert factory.call_args.kwargs["base_url"] == "https://api.x.ai/v1"


@pytest.mark.gate_p3
def test_flag_true_probe_pass_uses_vertex_maas() -> None:
    mock_client = MagicMock()
    mock_client.responses.create.return_value = _mock_response(
        citations=["https://cloud.google.com/vertex-ai"],
    )
    factory = MagicMock(return_value=mock_client)
    token_provider = MagicMock()
    token_provider.needs_refresh.return_value = True
    token_provider.get_access_token.return_value = "gcp-access-token"

    backend = GrokGroundingBackend(
        _maas_config(
            grok_grounding_auth="auto",
            grok_maas_web_search_enabled=True,
            grok_maas_capability_probe=True,
        ),
        client_factory=factory,
        maas_token_provider=token_provider,
    )
    # Init probe already called once; seed capable so search path is clear.
    backend._set_maas_capability(True)

    assert backend.auth_mode == "vertex_maas"
    assert backend.is_configured() is True

    result = backend.search(_params())

    assert result.success is True
    assert result.provider_native["grok_auth_mode"] == "vertex_maas"
    assert result.provider_native["grok_client_mode"] == "sync_openai"
    assert result.provider_native["grok_maas_web_search_capable"] is True
    expected_base = build_maas_openapi_base_url("maas-proj", "global")
    assert factory.call_args.kwargs["base_url"] == expected_base
    assert factory.call_args.kwargs["api_key"] == "gcp-access-token"
    call_kwargs = mock_client.responses.create.call_args.kwargs
    assert call_kwargs["model"] == "xai/grok-4.5"
    assert call_kwargs["tools"] == [{"type": "web_search"}]


@pytest.mark.gate_p3
def test_forced_vertex_maas_ignores_flag() -> None:
    mock_client = MagicMock()
    mock_client.responses.create.return_value = _mock_response(
        citations=["https://example.com/a"],
    )
    factory = MagicMock(return_value=mock_client)
    token_provider = MagicMock()
    token_provider.needs_refresh.return_value = True
    token_provider.get_access_token.return_value = "tok"

    backend = GrokGroundingBackend(
        _maas_config(
            grok_grounding_auth="vertex_maas",
            grok_maas_web_search_enabled=False,
            grok_maas_capability_probe=False,
        ),
        client_factory=factory,
        maas_token_provider=token_provider,
    )

    assert backend.auth_mode == "vertex_maas"
    assert backend.is_configured() is True
    result = backend.search(_params())
    assert result.success is True
    assert result.provider_native["grok_auth_mode"] == "vertex_maas"


@pytest.mark.gate_p3
def test_auto_enable_true_requires_probe_even_when_probe_flag_false() -> None:
    """Auto MaaS must not trust enable alone — capability cache/probe gates eligibility."""
    factory = MagicMock()
    token_provider = MagicMock()
    backend = GrokGroundingBackend(
        _maas_config(
            grok_grounding_auth="auto",
            grok_maas_web_search_enabled=True,
            grok_maas_capability_probe=False,
        ),
        client_factory=factory,
        maas_token_provider=token_provider,
    )
    backend._set_maas_capability(False)

    assert backend.auth_mode == "vertex_maas"
    assert backend.is_configured() is False
    factory.assert_not_called()

    backend._set_maas_capability(True)
    assert backend.is_configured() is True


@pytest.mark.gate_p3
def test_probe_fail_skips_auto_forced_fast_fails() -> None:
    factory = MagicMock()
    token_provider = MagicMock()
    token_provider.needs_refresh.return_value = False

    backend = GrokGroundingBackend(
        _maas_config(
            grok_grounding_auth="auto",
            grok_maas_web_search_enabled=True,
            grok_maas_capability_probe=True,
        ),
        client_factory=factory,
        maas_token_provider=token_provider,
    )
    backend._set_maas_capability(False)

    assert backend.auth_mode == "vertex_maas"
    assert backend.is_configured() is False
    factory.assert_not_called()

    forced = GrokGroundingBackend(
        _maas_config(
            grok_grounding_auth="vertex_maas",
            grok_maas_web_search_enabled=False,
            grok_maas_capability_probe=True,
        ),
        client_factory=factory,
        maas_token_provider=token_provider,
    )
    forced._set_maas_capability(False)
    assert forced.is_configured() is True
    result = forced.search(_params())
    assert result.success is False
    assert result.error_type == "maas_web_search_unsupported"
    # Fast-fail must not open a MaaS HTTP client when cache is negative.
    factory.assert_not_called()
