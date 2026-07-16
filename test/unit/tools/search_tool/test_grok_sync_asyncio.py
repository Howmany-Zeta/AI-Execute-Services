"""P3-03: Grok under asyncio consumer pattern + auto chain (§3.4)."""

from __future__ import annotations

import asyncio
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
        "enable_intent_analysis": False,
        "enable_context_tracking": False,
        "enable_intelligent_cache": False,
        "enable_quality_analysis": False,
        "enable_deduplication": False,
        "retry_attempts": 1,
    }
    base.update(overrides)
    return base


def _mock_response(*, citations: list[str], text: str = "grounded") -> MagicMock:
    response = MagicMock()
    response.output_text = text
    response.citations = citations
    response.output = []
    return response


def _tool_with_backends(
    *,
    gemini: FakeGroundingBackend,
    grok: GrokGroundingBackend | FakeGroundingBackend,
    cse: FakeGroundingBackend | None = None,
    **config_overrides: object,
) -> SearchTool:
    tool = SearchTool(config=_base_config(**config_overrides))
    registry = GroundingBackendRegistry()
    registry.register(gemini)
    registry.register(grok)
    registry.register(cse or FakeGroundingBackend("google_cse", configured=False))
    tool._registry = registry
    return tool


@pytest.mark.gate_p3
@pytest.mark.asyncio
async def test_grok_search_web_via_run_in_executor() -> None:
    mock_client = MagicMock()
    mock_client.responses.create.return_value = _mock_response(
        citations=["https://x.ai/news"],
        text="executor grounded",
    )
    live = GrokGroundingBackend(
        SearchTool.Config.model_construct(
            grok_api_key="test-grok-key",
            grounding_model_grok="grok-4.5",
            grounding_timeout_seconds=30.0,
            rate_limit_requests=100,
            rate_limit_window=86400,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=60,
        ),
        client_factory=MagicMock(return_value=mock_client),
    )
    tool = _tool_with_backends(
        gemini=FakeGroundingBackend("gemini", configured=False),
        grok=live,
        grounding_provider="grok",
    )

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: tool.search_web("What is xAI?", num_results=3, auto_enhance=False),
    )

    assert result["_search_metadata"]["backend_used"] == "grok"
    assert result["_search_metadata"]["grok_client_mode"] == "sync_openai"
    assert result["grounding_answer"] == "executor grounded"
    assert result["results"]
    mock_client.responses.create.assert_called_once()


@pytest.mark.gate_p3
@pytest.mark.asyncio
async def test_direct_search_web_from_async_does_not_nested_loop_crash() -> None:
    """Sync OpenAI path must not call asyncio.run; direct async-body call must not crash.

    Prefer ``run_in_executor`` for production consumers to avoid blocking the loop.
    """
    mock_client = MagicMock()
    mock_client.responses.create.return_value = _mock_response(
        citations=["https://x.ai/docs"],
        text="direct async-body call",
    )
    live = GrokGroundingBackend(
        SearchTool.Config.model_construct(
            grok_api_key="test-grok-key",
            grounding_model_grok="grok-4.5",
            grounding_timeout_seconds=30.0,
            rate_limit_requests=100,
            rate_limit_window=86400,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=60,
        ),
        client_factory=MagicMock(return_value=mock_client),
    )
    tool = _tool_with_backends(
        gemini=FakeGroundingBackend("gemini", configured=False),
        grok=live,
        grounding_provider="grok",
    )

    result = tool.search_web("xAI docs", auto_enhance=False)

    assert result["_search_metadata"]["backend_used"] == "grok"
    assert result["grounding_answer"] == "direct async-body call"


@pytest.mark.gate_p3
def test_auto_chain_gemini_fail_then_grok_success() -> None:
    mock_client = MagicMock()
    mock_client.responses.create.return_value = _mock_response(
        citations=["https://grok.example/hit"],
        text="grok after gemini fail",
    )
    live = GrokGroundingBackend(
        SearchTool.Config.model_construct(
            grok_api_key="test-grok-key",
            grounding_model_grok="grok-4.5",
            grounding_timeout_seconds=30.0,
            rate_limit_requests=100,
            rate_limit_window=86400,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=60,
        ),
        client_factory=MagicMock(return_value=mock_client),
    )
    gemini = FakeGroundingBackend("gemini", succeed=False, error="gemini down")
    cse = FakeGroundingBackend(
        "google_cse",
        citations=[{"url": "https://cse.example/1", "title": "CSE", "snippet": "x", "domain": "cse.example"}],
    )
    tool = _tool_with_backends(gemini=gemini, grok=live, cse=cse)

    result = tool.search_web("chain walk", auto_enhance=False)

    assert result["_search_metadata"]["backend_used"] == "grok"
    assert result["_search_metadata"]["provider_chain"] == ["gemini", "grok"]
    assert len(gemini.search_calls) == 1
    assert len(cse.search_calls) == 0
    assert result["grounding_answer"] == "grok after gemini fail"


@pytest.mark.gate_p3
def test_auto_chain_gemini_fail_grok_fail_then_cse() -> None:
    mock_client = MagicMock()
    mock_client.responses.create.side_effect = RuntimeError("grok unavailable")
    live = GrokGroundingBackend(
        SearchTool.Config.model_construct(
            grok_api_key="test-grok-key",
            grounding_model_grok="grok-4.5",
            grounding_timeout_seconds=30.0,
            rate_limit_requests=100,
            rate_limit_window=86400,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=60,
        ),
        client_factory=MagicMock(return_value=mock_client),
    )
    gemini = FakeGroundingBackend("gemini", succeed=False, error="gemini down")
    cse = FakeGroundingBackend(
        "google_cse",
        citations=[
            {
                "url": "https://cse.example/page",
                "title": "CSE Hit",
                "snippet": "from cse",
                "domain": "cse.example",
            }
        ],
    )
    tool = _tool_with_backends(
        gemini=gemini,
        grok=live,
        cse=cse,
        google_api_key="cse-key",
        google_cse_id="cse-id",
    )

    result = tool.search_web("fall through to cse", auto_enhance=False)

    assert result["_search_metadata"]["backend_used"] == "google_cse"
    assert result["_search_metadata"]["provider_chain"] == ["gemini", "grok", "google_cse"]
    assert len(gemini.search_calls) == 1
    assert mock_client.responses.create.call_count == 1
    assert len(cse.search_calls) == 1
    assert result["results"][0]["url"] == "https://cse.example/page"
