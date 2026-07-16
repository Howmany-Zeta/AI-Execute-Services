"""search_web / search_batch forward allowed_domains / blocked_domains (§3.6)."""

from __future__ import annotations

import pytest

from aiecs.tools.search_tool.backends.registry import GroundingBackendRegistry
from aiecs.tools.search_tool.core import SearchTool
from aiecs.tools.search_tool.schemas import SearchBatchSchema, SearchWebSchema
from test.unit.tools.search_tool.fakes import FakeGroundingBackend


def _tool_with_backend(backend: FakeGroundingBackend, **config: object) -> SearchTool:
    base: dict[str, object] = {
        "grounding_provider": "auto",
        "grounding_provider_chain": "gemini,grok,google_cse",
        "enable_intent_analysis": False,
        "enable_context_tracking": False,
        "enable_intelligent_cache": False,
        "enable_quality_analysis": False,
        "enable_deduplication": False,
    }
    base.update(config)
    tool = SearchTool(config=base)
    registry = GroundingBackendRegistry()
    registry.register(backend)
    registry.register(FakeGroundingBackend("grok", configured=False))
    registry.register(FakeGroundingBackend("google_cse", configured=False))
    tool._registry = registry
    return tool


@pytest.mark.gate_p1
def test_search_web_forwards_allowed_and_blocked_domains() -> None:
    gemini = FakeGroundingBackend(
        "gemini",
        citations=[
            {
                "url": "https://yougov.com/hit",
                "title": "survey",
                "snippet": "ok",
                "domain": "yougov.com",
            }
        ],
    )
    tool = _tool_with_backend(gemini, grounding_provider="gemini")

    out = tool.search_web(
        "tesla young people",
        auto_enhance=False,
        allowed_domains=["yougov.com", "pewresearch.org"],
        blocked_domains=["facebook.com"],
        grounding_provider="gemini",
    )

    assert out["_search_metadata"]["backend_used"] == "gemini"
    assert len(gemini.search_calls) == 1
    params = gemini.search_calls[0]
    assert params.allowed_domains == ["yougov.com", "pewresearch.org"]
    assert params.blocked_domains == ["facebook.com"]


@pytest.mark.gate_p1
def test_search_web_normalizes_empty_domain_lists_to_none() -> None:
    gemini = FakeGroundingBackend("gemini")
    tool = _tool_with_backend(gemini, grounding_provider="gemini")

    tool.search_web(
        "q",
        auto_enhance=False,
        allowed_domains=["", "  "],
        blocked_domains=[],
        grounding_provider="gemini",
    )

    params = gemini.search_calls[0]
    assert params.allowed_domains is None
    assert params.blocked_domains is None


@pytest.mark.gate_p1
def test_search_batch_forwards_domain_filters() -> None:
    gemini = FakeGroundingBackend("gemini")
    tool = _tool_with_backend(gemini, grounding_provider="gemini")

    tool.search_batch(
        ["q1", "q2"],
        auto_enhance=False,
        allowed_domains=["yougov.com"],
        blocked_domains=["facebook.com"],
        grounding_provider="gemini",
    )

    assert len(gemini.search_calls) == 2
    for call in gemini.search_calls:
        assert call.allowed_domains == ["yougov.com"]
        assert call.blocked_domains == ["facebook.com"]


@pytest.mark.gate_p1
def test_search_web_schema_includes_domain_filters() -> None:
    schema = SearchWebSchema(
        query="q",
        allowed_domains=["a.com"],
        blocked_domains=["b.com"],
    )
    assert schema.allowed_domains == ["a.com"]
    assert schema.blocked_domains == ["b.com"]
    batch = SearchBatchSchema(queries=["q"], allowed_domains=["a.com"])
    assert batch.allowed_domains == ["a.com"]


@pytest.mark.gate_p1
def test_search_web_forwards_exclude_terms_list() -> None:
    gemini = FakeGroundingBackend("gemini")
    tool = _tool_with_backend(gemini, grounding_provider="gemini")

    tool.search_web(
        "q",
        auto_enhance=False,
        exclude_terms=["spam", "ads"],
        grounding_provider="gemini",
    )

    params = gemini.search_calls[0]
    assert params.exclude_terms == ["spam", "ads"]


@pytest.mark.gate_p1
def test_search_web_normalizes_empty_exclude_terms_to_none() -> None:
    gemini = FakeGroundingBackend("gemini")
    tool = _tool_with_backend(gemini, grounding_provider="gemini")

    tool.search_web(
        "q",
        auto_enhance=False,
        exclude_terms=["", "  "],
        grounding_provider="gemini",
    )

    assert gemini.search_calls[0].exclude_terms is None


@pytest.mark.gate_p1
def test_exclude_terms_schema_is_list_str() -> None:
    web = SearchWebSchema(query="q", exclude_terms=["spam"])
    batch = SearchBatchSchema(queries=["q"], exclude_terms=["spam", "ads"])
    assert web.exclude_terms == ["spam"]
    assert batch.exclude_terms == ["spam", "ads"]
