"""P3-03: Grok sync search_batch — sequential calls, no deadlock (§3.4)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aiecs.tools.search_tool.backends.grok_grounding import GrokGroundingBackend
from aiecs.tools.search_tool.backends.registry import GroundingBackendRegistry
from aiecs.tools.search_tool.core import SearchTool
from test.unit.tools.search_tool.fakes import FakeGroundingBackend


def _base_config(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "grok_api_key": "test-grok-key",
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


def _mock_response(*, citations: list[str], text: str = "grounded") -> MagicMock:
    response = MagicMock()
    response.output_text = text
    response.citations = citations
    response.output = []
    return response


def _tool_with_live_grok(mock_client: MagicMock, **config_overrides: object) -> SearchTool:
    tool = SearchTool(config=_base_config(**config_overrides))
    live = GrokGroundingBackend(
        tool.config,
        client_factory=MagicMock(return_value=mock_client),
    )
    registry = GroundingBackendRegistry()
    registry.register(FakeGroundingBackend("gemini", configured=False))
    registry.register(live)
    registry.register(FakeGroundingBackend("google_cse", configured=False))
    tool._registry = registry
    return tool


@pytest.mark.gate_p3
def test_default_registry_wires_live_grok_backend() -> None:
    tool = SearchTool(
        config={
            "enable_intent_analysis": False,
            "enable_intelligent_cache": False,
            "enable_context_tracking": False,
        }
    )
    backend = tool._registry.get("grok")
    assert isinstance(backend, GrokGroundingBackend)


@pytest.mark.gate_p3
def test_search_batch_three_queries_sequential_sync_grok_no_deadlock() -> None:
    mock_client = MagicMock()
    mock_client.responses.create.side_effect = [
        _mock_response(citations=["https://example.com/1"], text="a1"),
        _mock_response(citations=["https://example.com/2"], text="a2"),
        _mock_response(citations=["https://example.com/3"], text="a3"),
    ]
    tool = _tool_with_live_grok(mock_client)

    result = tool.search_batch(
        queries=["q1 about alpha", "q2 about beta", "q3 about gamma"],
        num_results=3,
        auto_enhance=False,
    )

    assert mock_client.responses.create.call_count == 3
    assert result["_metadata"]["batch_pinned_backend"] == "grok"
    assert result["_metadata"]["per_query_backend_used"] == ["grok", "grok", "grok"]
    assert result["_metadata"]["batch_first_query_chain_attempted"] == ["gemini", "grok"]
    assert len(result["per_query"]) == 3
    assert all(bucket.get("success") is not False for bucket in result["per_query"])
    assert result["per_query"][0]["grounding_answer"] == "a1"
    assert result["per_query"][1]["_search_metadata"]["batch_used_pinned_backend"] is True
    assert result["per_query"][2]["_search_metadata"]["grok_client_mode"] == "sync_openai"

    inputs = [
        call.kwargs["input"][0]["content"]
        for call in mock_client.responses.create.call_args_list
    ]
    assert inputs == ["q1 about alpha", "q2 about beta", "q3 about gamma"]
