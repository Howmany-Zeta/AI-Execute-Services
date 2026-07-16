"""P1-06: _search_web_impl wired through GroundingRouter (§10)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aiecs.tools.search_tool.backends.registry import GroundingBackendRegistry
from aiecs.tools.search_tool.core import SearchTool
from test.unit.tools.search_tool.fakes import FakeGroundingBackend


def _cse_items() -> dict:
    return {
        "items": [
            {
                "title": "Example Result",
                "link": "https://example.com/page",
                "snippet": "An example snippet",
                "displayLink": "example.com",
            }
        ]
    }


def _tool_config(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "enable_intent_analysis": False,
        "enable_context_tracking": False,
        "enable_intelligent_cache": False,
        "retry_attempts": 1,
    }
    base.update(overrides)
    return base


@pytest.mark.gate_p1
def test_cse_only_caller_unchanged() -> None:
    mock_service = MagicMock()
    mock_list = MagicMock()
    mock_list.execute.return_value = _cse_items()
    mock_service.cse.return_value.list.return_value = mock_list

    tool = SearchTool(
        config=_tool_config(
            google_api_key="test-api-key",
            google_cse_id="test-cse-id",
            grounding_provider="auto",
        )
    )
    tool.service = mock_service

    result = tool.search_web("tesla popularity", num_results=5, auto_enhance=False)

    assert result["results"]
    assert result["results"][0]["link"] == "https://example.com/page"
    assert result["results"][0]["url"] == "https://example.com/page"
    assert result["_search_metadata"]["backend_used"] == "google_cse"
    assert "google_cse" in result["_search_metadata"]["provider_chain"]
    call_kwargs = mock_service.cse.return_value.list.call_args.kwargs
    assert call_kwargs["q"] == "tesla popularity"
    assert call_kwargs["cx"] == "test-cse-id"


@pytest.mark.gate_p1
def test_fake_grounding_success_without_cse_keys() -> None:
    tool = SearchTool(
        config=_tool_config(
            grounding_provider="auto",
            grounding_provider_chain="gemini,grok,google_cse",
        )
    )
    gemini = FakeGroundingBackend(
        "gemini",
        citations=[
            {
                "url": "https://grounding.example/hit",
                "title": "Grounding Hit",
                "snippet": "from gemini",
                "domain": "grounding.example",
            }
        ],
    )
    registry = GroundingBackendRegistry()
    registry.register(gemini)
    registry.register(FakeGroundingBackend("grok", configured=False))
    registry.register(FakeGroundingBackend("google_cse", configured=False))
    tool._registry = registry

    result = tool.search_web("gen z survey", num_results=3, auto_enhance=False)

    assert result["results"]
    assert result["results"][0]["link"] == "https://grounding.example/hit"
    assert result["results"][0]["url"] == "https://grounding.example/hit"
    assert result["_search_metadata"]["backend_used"] == "gemini"
    assert result["_search_metadata"]["provider_chain"] == ["gemini"]
    assert len(gemini.search_calls) == 1


@pytest.mark.gate_p1
def test_grounding_provider_google_uses_google_cse() -> None:
    mock_service = MagicMock()
    mock_list = MagicMock()
    mock_list.execute.return_value = _cse_items()
    mock_service.cse.return_value.list.return_value = mock_list

    tool = SearchTool(
        config=_tool_config(
            google_api_key="test-api-key",
            google_cse_id="test-cse-id",
            grounding_provider="google",
        )
    )
    tool.service = mock_service

    result = tool.search_web("annual report", num_results=5, auto_enhance=False)

    assert result["_search_metadata"]["backend_used"] == "google_cse"
    assert result["_metadata"]["backend_used"] == "google_cse"
    assert result["results"][0]["link"]
