"""P2-01: GeminiGroundingBackend Google GenAI API key path."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from aiecs.tools.search_tool.backends.gemini_grounding import GeminiGroundingBackend
from aiecs.tools.search_tool.backends.protocol import SearchCallParams
from aiecs.tools.search_tool.core import SearchTool


def _googleai_config(**overrides: object) -> SearchTool.Config:
    base = {
        "gemini_grounding_auth": "googleai",
        "gemini_api_key": "test-gemini-key",
        "grounding_model_gemini": "gemini-2.5-flash",
        "gemini_grounding_temperature": 1.0,
        "rate_limit_requests": 100,
        "rate_limit_window": 86400,
        "circuit_breaker_threshold": 5,
        "circuit_breaker_timeout": 60,
    }
    base.update(overrides)
    return SearchTool.Config.model_construct(**base)


def _params(**overrides: object) -> SearchCallParams:
    base = {
        "query": "tesla gen z popularity",
        "original_query": "tesla gen z popularity",
        "num_results": 5,
    }
    base.update(overrides)
    return SearchCallParams(**base)  # type: ignore[arg-type]


def _mock_response(*, uris: list[str] | None, text: str = "answer") -> MagicMock:
    chunks = []
    for uri in uris or []:
        chunks.append(
            SimpleNamespace(web=SimpleNamespace(uri=uri, title="T", domain="example.com"))
        )
    response = MagicMock()
    response.text = text
    response.candidates = [
        SimpleNamespace(grounding_metadata=SimpleNamespace(grounding_chunks=chunks))
    ]
    return response


@pytest.mark.gate_p2
def test_googleai_success_grounding_chunks_to_citations() -> None:
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _mock_response(
        uris=["https://example.com/1", "https://example.com/2"]
    )
    factory = MagicMock(return_value=mock_client)
    backend = GeminiGroundingBackend(_googleai_config(), client_factory=factory)

    result = backend.search(_params(date_restrict="m3", file_type="pdf"))

    assert result.success is True
    assert len(result.citations) == 2
    assert result.citations[0]["url"] == "https://example.com/1"
    assert result.answer == "answer"
    assert result.provider_native is not None
    assert result.provider_native["gemini_auth_mode"] == "googleai"
    assert "date_restrict" in result.params_ignored
    assert "file_type" in result.params_ignored
    factory.assert_called_once_with(api_key="test-gemini-key")
    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-2.5-flash"
    assert call_kwargs["config"].temperature == 1.0
    assert call_kwargs["config"].tools[0].google_search is not None


@pytest.mark.gate_p2
def test_googleai_empty_chunks_returns_structured_fail() -> None:
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _mock_response(uris=[])
    backend = GeminiGroundingBackend(
        _googleai_config(),
        client_factory=MagicMock(return_value=mock_client),
    )

    result = backend.search(_params())

    assert result.success is False
    assert result.error_type == "empty_grounding_chunks"
    assert result.citations == []


@pytest.mark.gate_p2
def test_googleai_401_returns_auth_failure() -> None:
    from google.genai import errors as genai_errors

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = genai_errors.ClientError(
        401,
        {"error": {"message": "invalid api key", "status": "UNAUTHENTICATED", "code": 401}},
    )
    backend = GeminiGroundingBackend(
        _googleai_config(),
        client_factory=MagicMock(return_value=mock_client),
    )

    result = backend.search(_params())

    assert result.success is False
    assert result.error_type == "auth"
    assert "invalid api key" in (result.error or "")


@pytest.mark.gate_p2
def test_googleai_timeout_returns_structured_fail() -> None:
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = TimeoutError("request timed out")
    backend = GeminiGroundingBackend(
        _googleai_config(),
        client_factory=MagicMock(return_value=mock_client),
    )

    result = backend.search(_params())

    assert result.success is False
    assert result.error_type == "timeout"
