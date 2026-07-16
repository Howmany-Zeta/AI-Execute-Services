"""P2-03: searchEntryPoint passthrough + grounding-only search_web (§3.13)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from aiecs.tools.search_tool.backends.gemini_grounding import GeminiGroundingBackend
from aiecs.tools.search_tool.backends.protocol import SearchCallParams
from aiecs.tools.search_tool.backends.registry import GroundingBackendRegistry
from aiecs.tools.search_tool.core import SearchTool
from test.unit.tools.search_tool.fakes import FakeGroundingBackend


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


def _grounded_response(
    *,
    uris: list[str],
    rendered_content: str | None = None,
    web_search_queries: list[str] | None = None,
) -> MagicMock:
    chunks = [
        SimpleNamespace(web=SimpleNamespace(uri=u, title=f"T{i}", domain="example.com"))
        for i, u in enumerate(uris)
    ]
    entry = None
    if rendered_content is not None:
        entry = SimpleNamespace(rendered_content=rendered_content, sdk_blob=None)
    meta = SimpleNamespace(
        grounding_chunks=chunks,
        web_search_queries=web_search_queries or ["Tesla Gen Z popularity"],
        search_entry_point=entry,
    )
    response = MagicMock()
    response.text = "Synthesized grounding answer"
    response.candidates = [SimpleNamespace(grounding_metadata=meta)]
    return response


@pytest.mark.gate_p2
def test_search_entrypoint_sets_requires_search_suggestions_ui_true() -> None:
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _grounded_response(
        uris=["https://example.com/a"],
        rendered_content="<!-- Google Search Suggestions HTML -->",
    )
    backend = GeminiGroundingBackend(
        _googleai_config(),
        client_factory=MagicMock(return_value=mock_client),
    )

    result = backend.search(
        SearchCallParams(query="tesla gen z", original_query="tesla gen z", num_results=5)
    )

    assert result.success is True
    gg = result.provider_native["gemini_grounding"]
    assert gg["requires_search_suggestions_ui"] is True
    assert gg["search_entry_point"]["rendered_content"] == "<!-- Google Search Suggestions HTML -->"
    assert gg["web_search_queries"] == ["Tesla Gen Z popularity"]


@pytest.mark.gate_p2
def test_without_search_entrypoint_requires_ui_false() -> None:
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _grounded_response(
        uris=["https://example.com/a"],
        rendered_content=None,
    )
    backend = GeminiGroundingBackend(
        _googleai_config(),
        client_factory=MagicMock(return_value=mock_client),
    )

    result = backend.search(
        SearchCallParams(query="q", original_query="q", num_results=3)
    )

    gg = result.provider_native["gemini_grounding"]
    assert gg["requires_search_suggestions_ui"] is False
    assert gg["search_entry_point"] == {}


@pytest.mark.gate_p2
def test_forced_gemini_provider_backend_used_gemini() -> None:
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _grounded_response(
        uris=["https://pewresearch.org/tesla-genz"],
        rendered_content="<div>suggestions</div>",
    )
    tool = SearchTool(
        config={
            "gemini_api_key": "test-gemini-key",
            "grounding_provider": "gemini",
            "enable_intent_analysis": False,
            "enable_context_tracking": False,
            "enable_intelligent_cache": False,
            "enable_quality_analysis": False,
        }
    )
    live = GeminiGroundingBackend(tool.config, client_factory=MagicMock(return_value=mock_client))
    registry = GroundingBackendRegistry()
    registry.register(live)
    registry.register(FakeGroundingBackend("grok", configured=False))
    registry.register(FakeGroundingBackend("google_cse", configured=False))
    tool._registry = registry

    result = tool.search_web("Why is Tesla popular among Gen Z?", auto_enhance=False)

    assert result["_search_metadata"]["backend_used"] == "gemini"
    assert result["_search_metadata"]["gemini_auth_mode"] == "googleai"
    assert result["_search_metadata"]["gemini_grounding"]["requires_search_suggestions_ui"] is True
    assert result["grounding_answer"] == "Synthesized grounding answer"
    assert result["results"]
    assert result["results"][0]["link"] == "https://pewresearch.org/tesla-genz"


@pytest.mark.gate_p2
def test_grounding_only_deployment_search_web_without_cse() -> None:
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _grounded_response(
        uris=["https://kpmg.com/tesla-millennials"],
    )
    tool = SearchTool(
        config={
            "gemini_api_key": "only-gemini-key",
            "grounding_provider": "auto",
            "enable_intent_analysis": False,
            "enable_context_tracking": False,
            "enable_intelligent_cache": False,
            "enable_quality_analysis": False,
        }
    )
    assert not tool._is_cse_configured()

    live = GeminiGroundingBackend(tool.config, client_factory=MagicMock(return_value=mock_client))
    registry = GroundingBackendRegistry()
    registry.register(live)
    registry.register(FakeGroundingBackend("grok", configured=False))
    registry.register(FakeGroundingBackend("google_cse", configured=False))
    tool._registry = registry

    result = tool.search_web("Tesla Gen Z brand perception survey", auto_enhance=False)

    assert result["_search_metadata"]["backend_used"] == "gemini"
    assert "gemini_grounding" in result["_search_metadata"]
    assert result["_search_metadata"]["gemini_grounding"]["requires_search_suggestions_ui"] is False
    assert len(result["results"]) >= 1


@pytest.mark.gate_p2
def test_demographic_fixture_mocked_gemini_nonempty_results() -> None:
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _grounded_response(
        uris=[
            "https://yougov.com/tesla-gen-z",
            "https://pewresearch.org/gen-z-ev",
        ],
        web_search_queries=["Tesla Gen Z popularity"],
    )
    tool = SearchTool(
        config={
            "gemini_api_key": "test-gemini-key",
            "grounding_provider": "gemini",
            "enable_intent_analysis": False,
            "enable_context_tracking": False,
            "enable_intelligent_cache": False,
            "enable_quality_analysis": False,
        }
    )
    live = GeminiGroundingBackend(tool.config, client_factory=MagicMock(return_value=mock_client))
    tool._registry = GroundingBackendRegistry()
    tool._registry.register(live)

    result = tool.search_web("Why is Tesla popular among young people?", auto_enhance=False)

    assert result["_search_metadata"]["backend_used"] == "gemini"
    assert result["results"]
    assert all(item.get("link") for item in result["results"])
    assert "gemini_grounding" in result["_search_metadata"]
    assert result["_search_metadata"]["gemini_grounding"]["web_search_queries"] == [
        "Tesla Gen Z popularity"
    ]


@pytest.mark.gate_p2
def test_cse_response_has_no_gemini_grounding_block() -> None:
    mock_service = MagicMock()
    mock_list = MagicMock()
    mock_list.execute.return_value = {
        "items": [
            {
                "title": "CSE Hit",
                "link": "https://cse.example/hit",
                "snippet": "snippet",
                "displayLink": "cse.example",
            }
        ]
    }
    mock_service.cse.return_value.list.return_value = mock_list

    tool = SearchTool(
        config={
            "google_api_key": "k",
            "google_cse_id": "cx",
            "grounding_provider": "google_cse",
            "enable_intent_analysis": False,
            "enable_context_tracking": False,
            "enable_intelligent_cache": False,
            "enable_quality_analysis": False,
        }
    )
    tool.service = mock_service

    result = tool.search_web("query", auto_enhance=False)

    assert result["_search_metadata"]["backend_used"] == "google_cse"
    assert "gemini_grounding" not in result["_search_metadata"]
