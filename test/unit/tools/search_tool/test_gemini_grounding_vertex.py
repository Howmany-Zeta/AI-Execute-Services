"""P2-02: GeminiGroundingBackend Vertex credentials path."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from aiecs.tools.search_tool.backends.gemini_grounding import GeminiGroundingBackend
from aiecs.tools.search_tool.backends.protocol import SearchCallParams
from aiecs.tools.search_tool.core import SearchTool


def _vertex_config(**overrides: object) -> SearchTool.Config:
    base = {
        "gemini_grounding_auth": "auto",
        "vertex_project_id": "test-project",
        "vertex_location": "global",
        "google_application_credentials_vertex_gemini": "/tmp/fake-vertex-gemini.json",
        "grounding_model_gemini": "gemini-2.5-flash",
        "gemini_grounding_temperature": 1.0,
        "rate_limit_requests": 100,
        "rate_limit_window": 86400,
        "circuit_breaker_threshold": 5,
        "circuit_breaker_timeout": 60,
    }
    base.update(overrides)
    return SearchTool.Config.model_construct(**base)


def _params(query: str = "tesla gen z") -> SearchCallParams:
    return SearchCallParams(query=query, original_query=query, num_results=5)


def _mock_grounded_response(*uris: str) -> MagicMock:
    chunks = []
    for uri in uris:
        chunks.append(
            SimpleNamespace(web=SimpleNamespace(uri=uri, title=f"Title {uri}", domain="example.com"))
        )
    response = MagicMock()
    response.text = "grounded answer"
    response.candidates = [SimpleNamespace(grounding_metadata=SimpleNamespace(grounding_chunks=chunks))]
    return response


@pytest.mark.gate_p2
def test_vertex_client_success_returns_citations() -> None:
    config = _vertex_config(gemini_grounding_auth="vertex")
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _mock_grounded_response(
        "https://example.com/a",
        "https://example.com/b",
    )
    factory = MagicMock(return_value=mock_client)

    backend = GeminiGroundingBackend(config, client_factory=factory)
    backend._load_vertex_credentials = MagicMock(return_value=MagicMock(name="creds"))  # type: ignore[method-assign]

    result = backend.search(_params())

    assert result.success is True
    assert result.provider_native is not None
    assert result.provider_native["gemini_auth_mode"] == "vertex"
    assert len(result.citations) == 2
    assert result.citations[0]["url"] == "https://example.com/a"

    factory.assert_called_once()
    call_kwargs = factory.call_args.kwargs
    assert call_kwargs["vertexai"] is True
    assert call_kwargs["project"] == "test-project"
    assert call_kwargs["location"] == "global"
    assert call_kwargs["http_options"].api_version == "v1"


@pytest.mark.gate_p2
def test_auto_gemini_api_key_wins_over_vertex_creds() -> None:
    config = _vertex_config(
        gemini_grounding_auth="auto",
        gemini_api_key="search-tool-gemini-key",
    )
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _mock_grounded_response("https://example.com/g")
    factory = MagicMock(return_value=mock_client)
    backend = GeminiGroundingBackend(config, client_factory=factory)

    assert backend.auth_mode == "googleai"
    result = backend.search(_params())

    assert result.success is True
    assert result.provider_native is not None
    assert result.provider_native["gemini_auth_mode"] == "googleai"
    factory.assert_called_once_with(api_key="search-tool-gemini-key")


@pytest.mark.gate_p2
def test_vertex_only_creds_resolve_auth_mode_vertex() -> None:
    config = _vertex_config(gemini_grounding_auth="auto")
    # No gemini_api_key
    backend = GeminiGroundingBackend(config)

    assert backend.is_configured() is True
    assert backend.auth_mode == "vertex"


@pytest.mark.gate_p2
def test_enterprise_env_uses_enterprise_web_search_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_GENAI_USE_ENTERPRISE", "true")
    config = _vertex_config(gemini_grounding_auth="vertex")
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _mock_grounded_response("https://example.com/e")
    factory = MagicMock(return_value=mock_client)
    backend = GeminiGroundingBackend(config, client_factory=factory)
    backend._load_vertex_credentials = MagicMock(return_value=MagicMock(name="creds"))  # type: ignore[method-assign]

    result = backend.search(
        SearchCallParams(
            query="tesla gen z",
            original_query="tesla gen z",
            num_results=5,
            blocked_domains=["facebook.com", "twitter.com"],
        )
    )

    assert result.success is True
    assert result.provider_native is not None
    assert result.provider_native["enterprise_web_search"] is True
    assert result.provider_native["exclude_domains_applied"] == ["facebook.com", "twitter.com"]
    gen_config = mock_client.models.generate_content.call_args.kwargs["config"]
    tool = gen_config.tools[0]
    assert tool.enterprise_web_search is not None
    assert tool.google_search is None
    assert tool.enterprise_web_search.exclude_domains == ["facebook.com", "twitter.com"]


@pytest.mark.gate_p2
def test_include_raw_grounding_serializes_metadata() -> None:
    grounding_meta = SimpleNamespace(
        web_search_queries=["q1"],
        grounding_chunks=[
            SimpleNamespace(web=SimpleNamespace(uri="https://example.com/a", title="A", domain="example.com"))
        ],
        grounding_supports=[SimpleNamespace(confidence_scores=[0.9], grounding_chunk_indices=[0])],
        search_entry_point=SimpleNamespace(rendered_content="<div/>"),
    )
    response = SimpleNamespace(
        text="answer",
        candidates=[SimpleNamespace(grounding_metadata=grounding_meta)],
    )

    config = _vertex_config(
        gemini_grounding_auth="vertex",
        gemini_include_raw_grounding=True,
    )
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = response
    factory = MagicMock(return_value=mock_client)
    backend = GeminiGroundingBackend(config, client_factory=factory)
    backend._load_vertex_credentials = MagicMock(return_value=MagicMock(name="creds"))  # type: ignore[method-assign]

    result = backend.search(_params())

    assert result.success is True
    assert result.provider_native is not None
    meta = result.provider_native["grounding_metadata"]
    assert meta["web_search_queries"] == ["q1"]
    assert meta["grounding_chunks"][0]["web"]["uri"] == "https://example.com/a"
    assert "grounding_supports" in meta
    assert result.provider_native["generate_content_response"]["text"] == "answer"
