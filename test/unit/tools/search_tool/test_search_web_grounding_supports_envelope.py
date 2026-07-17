"""Layer A: search_web / search_batch expose grounding_chunks + grounding_supports."""

from __future__ import annotations

import pytest

from aiecs.tools.search_tool.backends.registry import GroundingBackendRegistry
from aiecs.tools.search_tool.core import SearchTool
from test.unit.tools.search_tool.fakes import FakeGroundingBackend


def _tool_config(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "enable_intent_analysis": False,
        "enable_context_tracking": False,
        "enable_intelligent_cache": False,
        "enable_quality_analysis": False,
        "enable_deduplication": False,
        "grounding_provider": "auto",
        "retry_attempts": 1,
    }
    base.update(overrides)
    return base


def _alignment_payload() -> tuple[list[dict], list[dict], list[dict]]:
    citations = [
        {
            "url": f"https://example.com/src{i}",
            "title": f"Source {i}",
            "domain": f"src{i}.example",
            "snippet": "",
        }
        for i in range(3)
    ]
    chunks = [
        {
            "index": i,
            "domain": f"src{i}.example",
            "title": f"Source {i}",
            "url": f"https://example.com/src{i}",
        }
        for i in range(9)
    ]
    supports = [
        {
            "grounding_chunk_indices": [i % 9],
            "segment": {"start_index": i * 5, "end_index": i * 5 + 4, "text": f"t{i:02d}"},
        }
        for i in range(11)
    ]
    return citations, chunks, supports


def _registry_with_gemini(gemini: FakeGroundingBackend) -> GroundingBackendRegistry:
    registry = GroundingBackendRegistry()
    registry.register(gemini)
    registry.register(FakeGroundingBackend("grok", configured=False))
    registry.register(FakeGroundingBackend("google_cse", configured=False))
    return registry


@pytest.mark.gate_p4
def test_search_web_envelope_includes_grounding_supports() -> None:
    citations, chunks, supports = _alignment_payload()
    tool = SearchTool(config=_tool_config())
    tool._registry = _registry_with_gemini(
        FakeGroundingBackend(
            "gemini",
            citations=citations,
            grounding_chunks=chunks,
            grounding_supports=supports,
        )
    )

    result = tool.search_web("tesla gen z", num_results=3, auto_enhance=False)

    assert len(result["results"]) == 3
    assert len(result["grounding_chunks"]) == 9
    assert len(result["grounding_supports"]) == 11
    assert result["grounding_chunks"][8]["index"] == 8
    assert result["grounding_supports"][0]["segment"]["text"] == "t00"


@pytest.mark.gate_p4
def test_search_batch_bucket_includes_grounding_supports() -> None:
    citations, chunks, supports = _alignment_payload()
    tool = SearchTool(config=_tool_config())
    tool._registry = _registry_with_gemini(
        FakeGroundingBackend(
            "gemini",
            citations=citations,
            grounding_chunks=chunks,
            grounding_supports=supports,
        )
    )

    batch = tool.search_batch(queries=["tesla gen z"], num_results=3, auto_enhance=False)
    bucket = batch["per_query"][0]

    assert len(bucket["grounding_chunks"]) == 9
    assert len(bucket["grounding_supports"]) == 11
