"""Layer A: lightweight grounding_supports / grounding_chunks projection."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from aiecs.tools.search_tool.backends.gemini_grounding import GeminiGroundingBackend
from aiecs.tools.search_tool.backends.protocol import SearchCallParams
from aiecs.tools.search_tool.core import SearchTool


def _vertex_config(**overrides: object) -> SearchTool.Config:
    base = {
        "gemini_grounding_auth": "vertex",
        "vertex_project_id": "test-project",
        "vertex_location": "global",
        "google_application_credentials_vertex_gemini": "/tmp/fake-vertex-gemini.json",
        "grounding_model_gemini": "gemini-2.5-flash",
        "gemini_grounding_temperature": 1.0,
        "gemini_include_raw_grounding": False,
        "gemini_include_grounding_supports": True,
        "rate_limit_requests": 100,
        "rate_limit_window": 86400,
        "circuit_breaker_threshold": 5,
        "circuit_breaker_timeout": 60,
    }
    base.update(overrides)
    return SearchTool.Config.model_construct(**base)


def _params(query: str = "why Tesla so popular among young people") -> SearchCallParams:
    return SearchCallParams(query=query, original_query=query, num_results=3)


def _fixture_answer_and_alignment() -> tuple[str, SimpleNamespace]:
    """9 chunks + 11 supports shaped like the consumer enterprise raw fixture."""
    domains = [
        "gallup.com",
        "reuters.com",
        "caranddriver.com",
        "edmunds.com",
        "consumerreports.org",
        "theverge.com",
        "forbes.com",
        "cnbc.com",
        "ucdavis.edu",
    ]
    chunks = [
        SimpleNamespace(
            web=SimpleNamespace(
                uri=f"https://example.com/{domain}/article",
                title=domain,
                domain=domain,
            )
        )
        for domain in domains
    ]
    # Compact spans covering contiguous regions of a synthetic answer.
    span_specs: list[tuple[list[int], str]] = [
        ([0], "Young adults, which include Gen Z and Millennials, continue to show interest"),
        ([0], "However, this interest has seen a decline from 2023 levels"),
        ([1], "This expanding market is anticipated to attract a wider range of buyers"),
        ([2], "For Gen Z and Millennial car buyers, online purchasing is a significant draw"),
        ([3], "Electric vehicles, including Teslas, did not rank among the top 10 most popular cars"),
        ([4], "Battery range was also a crucial attribute"),
        ([4], "Tesla CEO Elon Musk was perceived as a drawback by some non-Tesla EV owners"),
        ([5], "Public opinion regarding the Tesla Cybertruck in 2024 was largely negative"),
        ([6], "Despite Tesla brand appeal as a desired workplace for Gen Z students"),
        ([7], "Tesla experienced a significant drop in car sales in 2025"),
        ([8], "Registrations for Tesla vehicles in California have also seen a decline"),
    ]
    parts: list[str] = []
    supports: list[SimpleNamespace] = []
    cursor = 0
    for indices, text in span_specs:
        if parts:
            parts.append(" ")
            cursor += 1
        start = cursor
        parts.append(text)
        cursor += len(text)
        supports.append(
            SimpleNamespace(
                grounding_chunk_indices=list(indices),
                segment=SimpleNamespace(start_index=start, end_index=cursor, text=text),
            )
        )
    answer = "".join(parts)
    grounding_meta = SimpleNamespace(
        grounding_chunks=chunks,
        grounding_supports=supports,
        web_search_queries=["tesla gen z"],
    )
    return answer, grounding_meta


@pytest.mark.gate_p2
def test_project_grounding_alignment_nine_chunks_eleven_supports() -> None:
    answer, grounding_meta = _fixture_answer_and_alignment()
    chunks, supports = GeminiGroundingBackend._project_grounding_alignment(grounding_meta)

    assert len(chunks) == 9
    assert len(supports) == 11
    assert [c["index"] for c in chunks] == list(range(9))
    assert chunks[0]["domain"] == "gallup.com"
    assert chunks[8]["domain"] == "ucdavis.edu"

    for support in supports:
        segment = support["segment"]
        start = segment["start_index"]
        end = segment["end_index"]
        assert segment["text"] == answer[start:end]


@pytest.mark.gate_p2
def test_supports_present_when_raw_grounding_disabled() -> None:
    answer, grounding_meta = _fixture_answer_and_alignment()
    response = SimpleNamespace(
        text=answer,
        candidates=[SimpleNamespace(grounding_metadata=grounding_meta)],
    )
    config = _vertex_config(gemini_include_raw_grounding=False)
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = response
    factory = MagicMock(return_value=mock_client)
    backend = GeminiGroundingBackend(config, client_factory=factory)
    backend._load_vertex_credentials = MagicMock(return_value=MagicMock(name="creds"))  # type: ignore[method-assign]

    result = backend.search(_params())

    assert result.success is True
    assert len(result.grounding_chunks) == 9
    assert len(result.grounding_supports) == 11
    assert result.provider_native is not None
    assert "generate_content_response" not in result.provider_native
    assert "grounding_metadata" not in result.provider_native


@pytest.mark.gate_p2
def test_kill_switch_omits_supports() -> None:
    answer, grounding_meta = _fixture_answer_and_alignment()
    response = SimpleNamespace(
        text=answer,
        candidates=[SimpleNamespace(grounding_metadata=grounding_meta)],
    )
    config = _vertex_config(gemini_include_grounding_supports=False)
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = response
    factory = MagicMock(return_value=mock_client)
    backend = GeminiGroundingBackend(config, client_factory=factory)
    backend._load_vertex_credentials = MagicMock(return_value=MagicMock(name="creds"))  # type: ignore[method-assign]

    result = backend.search(_params())

    assert result.success is True
    assert result.grounding_chunks == []
    assert result.grounding_supports == []


@pytest.mark.gate_p2
def test_segment_text_omitted_when_config_false() -> None:
    answer, grounding_meta = _fixture_answer_and_alignment()
    chunks, supports = GeminiGroundingBackend._project_grounding_alignment(
        grounding_meta,
        include_segment_text=False,
    )
    assert len(chunks) == 9
    assert len(supports) == 11
    for support in supports:
        assert "text" not in support["segment"]
        assert "start_index" in support["segment"]
        assert "end_index" in support["segment"]
