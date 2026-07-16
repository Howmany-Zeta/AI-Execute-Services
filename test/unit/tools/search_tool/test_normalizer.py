"""P4-01: normalize_grounding_result citation tags + Gemini blocked_domains."""

from __future__ import annotations

import pytest

from aiecs.tools.search_tool.backends.protocol import BackendRawResult
from aiecs.tools.search_tool.backends.registry import GroundingBackendRegistry
from aiecs.tools.search_tool.core import SearchTool
from aiecs.tools.search_tool.normalizer import (
    filter_blocked_domain_citations,
    normalize_grounding_result,
)
from test.unit.tools.search_tool.fakes import FakeGroundingBackend


def _gemini_shaped_raw() -> BackendRawResult:
    return BackendRawResult(
        success=True,
        answer="Gemini synthesized answer",
        citations=[
            {
                "url": "https://www.yougov.com/topics/tesla",
                "title": "YouGov Tesla",
                "domain": "www.yougov.com",
                "snippet": "",
            },
            {
                "url": "https://example.com/report",
                "title": "Example Report",
                "domain": "example.com",
                "snippet": "short note",
            },
        ],
        backend="gemini",
        params_applied=["blocked_domains"],
        params_ignored=["date_restrict", "safe_search", "file_type", "start_index"],
        provider_native={"gemini_auth_mode": "googleai"},
    )


def _grok_shaped_raw() -> BackendRawResult:
    return BackendRawResult(
        success=True,
        answer="Grok grounded answer",
        citations=[
            {"url": "https://x.ai/news", "title": "xAI News", "domain": "x.ai", "snippet": ""},
            {
                "url": "https://docs.x.ai/developers",
                "title": "xAI Docs",
                "domain": "docs.x.ai",
                "snippet": "API notes",
            },
        ],
        backend="grok",
        params_applied=["query"],
        params_ignored=["date_restrict"],
        provider_native={"grok_auth_mode": "xai", "grok_client_mode": "sync_openai"},
    )


@pytest.mark.gate_p4
def test_normalize_gemini_shape_has_link_fields_and_tags() -> None:
    partial = normalize_grounding_result(_gemini_shaped_raw(), "gemini")

    assert len(partial["results"]) == 2
    first = partial["results"][0]
    assert first["link"] == "https://www.yougov.com/topics/tesla"
    assert first["url"] == first["link"]
    assert first["displayLink"] == "www.yougov.com"
    assert first["snippet"] == ""
    assert first["_result_source"] == "grounding_citation"
    assert first["_citation_rank"] == 1
    assert partial["results"][1]["_citation_rank"] == 2
    assert partial["grounding_answer"] == "Gemini synthesized answer"
    assert partial["grounding_citations"] == [
        "https://www.yougov.com/topics/tesla",
        "https://example.com/report",
    ]
    assert partial["_search_metadata"]["backend_used"] == "gemini"
    assert partial["_search_metadata"]["params_applied"] == ["blocked_domains"]
    assert "date_restrict" in partial["_search_metadata"]["params_ignored"]


@pytest.mark.gate_p4
def test_normalize_grok_shape_has_link_fields_and_tags() -> None:
    partial = normalize_grounding_result(_grok_shaped_raw(), "grok")

    assert len(partial["results"]) == 2
    assert partial["results"][0]["link"].startswith("https://")
    assert partial["results"][0]["url"] == partial["results"][0]["link"]
    assert partial["results"][0]["displayLink"] == "x.ai"
    assert partial["results"][0]["_result_source"] == "grounding_citation"
    assert partial["results"][1]["_citation_rank"] == 2
    assert partial["grounding_answer"] == "Grok grounded answer"
    assert partial["_search_metadata"]["params_ignored"] == ["date_restrict"]


@pytest.mark.gate_p4
def test_gemini_blocked_domains_post_filter() -> None:
    raw = BackendRawResult(
        success=True,
        answer="filtered",
        citations=[
            {
                "url": "https://www.facebook.com/tesla",
                "title": "Facebook",
                "domain": "www.facebook.com",
                "snippet": "",
            },
            {
                "url": "https://www.yougov.com/topics/tesla",
                "title": "YouGov",
                "domain": "www.yougov.com",
                "snippet": "",
            },
        ],
        backend="gemini",
        params_applied=["blocked_domains"],
    )

    partial = normalize_grounding_result(
        raw,
        "gemini",
        blocked_domains=["facebook.com"],
    )

    assert len(partial["results"]) == 1
    assert partial["results"][0]["displayLink"] == "www.yougov.com"
    assert partial["results"][0]["_citation_rank"] == 1
    assert partial["grounding_citations"] == ["https://www.yougov.com/topics/tesla"]


@pytest.mark.gate_p4
def test_filter_blocked_domain_citations_helper() -> None:
    kept = filter_blocked_domain_citations(
        [
            {"url": "https://m.facebook.com/x", "domain": "m.facebook.com"},
            {"url": "https://news.example.com/a", "domain": "news.example.com"},
        ],
        ["facebook.com"],
    )
    assert len(kept) == 1
    assert kept[0]["domain"] == "news.example.com"


@pytest.mark.gate_p4
def test_search_web_wires_normalizer_tags() -> None:
    tool = SearchTool(
        config={
            "enable_intent_analysis": False,
            "enable_context_tracking": False,
            "enable_intelligent_cache": False,
            "enable_quality_analysis": False,
            "enable_deduplication": False,
            "grounding_provider": "auto",
        }
    )
    gemini = FakeGroundingBackend(
        "gemini",
        citations=[
            {
                "url": "https://grounding.example/hit",
                "title": "Hit",
                "snippet": "from gemini",
                "domain": "grounding.example",
            }
        ],
    )
    # Attach answer via search override
    original_search = gemini.search

    def search_with_answer(params):
        result = original_search(params)
        result.answer = "synthesized"
        result.params_ignored = ["date_restrict"]
        return result

    gemini.search = search_with_answer  # type: ignore[method-assign]

    registry = GroundingBackendRegistry()
    registry.register(gemini)
    registry.register(FakeGroundingBackend("grok", configured=False))
    registry.register(FakeGroundingBackend("google_cse", configured=False))
    tool._registry = registry

    result = tool.search_web("gen z survey", num_results=3, auto_enhance=False)

    assert result["results"][0]["link"] == "https://grounding.example/hit"
    assert result["results"][0]["url"] == "https://grounding.example/hit"
    assert result["results"][0]["_result_source"] == "grounding_citation"
    assert result["results"][0]["_citation_rank"] == 1
    assert result["grounding_answer"] == "synthesized"
    assert result["grounding_citations"] == ["https://grounding.example/hit"]
    assert result["_search_metadata"]["params_ignored"] == ["date_restrict"]
