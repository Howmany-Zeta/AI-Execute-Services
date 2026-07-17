"""Layer A: normalize_grounding_result passes grounding_chunks / grounding_supports."""

from __future__ import annotations

import pytest

from aiecs.tools.search_tool.backends.protocol import BackendRawResult
from aiecs.tools.search_tool.normalizer import (
    filter_blocked_domain_grounding_alignment,
    normalize_grounding_result,
)


def _nine_chunk_raw(*, num_citation_urls: int = 9) -> BackendRawResult:
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
    citations = [
        {
            "url": f"https://example.com/{d}/a",
            "title": d,
            "domain": d,
            "snippet": "",
        }
        for d in domains[:num_citation_urls]
    ]
    chunks = [
        {
            "index": i,
            "domain": d,
            "title": d,
            "url": f"https://example.com/{d}/a",
        }
        for i, d in enumerate(domains)
    ]
    supports = [
        {
            "grounding_chunk_indices": [i % 9],
            "segment": {"start_index": i * 10, "end_index": i * 10 + 5, "text": f"span{i}"},
        }
        for i in range(11)
    ]
    return BackendRawResult(
        success=True,
        answer="x" * 120,
        citations=citations,
        grounding_chunks=chunks,
        grounding_supports=supports,
        backend="gemini",
    )


@pytest.mark.gate_p4
def test_normalize_includes_chunks_and_supports() -> None:
    partial = normalize_grounding_result(_nine_chunk_raw(), "gemini")

    assert len(partial["grounding_chunks"]) == 9
    assert len(partial["grounding_supports"]) == 11
    assert partial["grounding_chunks"][0]["index"] == 0
    assert partial["grounding_supports"][0]["grounding_chunk_indices"] == [0]


@pytest.mark.gate_p4
def test_num_results_truncates_results_not_chunk_table() -> None:
    partial = normalize_grounding_result(_nine_chunk_raw(), "gemini", num_results=3)

    assert len(partial["results"]) == 3
    assert len(partial["grounding_citations"]) == 3
    assert len(partial["grounding_chunks"]) == 9
    assert {c["index"] for c in partial["grounding_chunks"]} == set(range(9))
    assert len(partial["grounding_supports"]) == 11


@pytest.mark.gate_p4
def test_blocked_domain_prunes_chunks_and_orphan_supports() -> None:
    chunks = [
        {"index": 0, "domain": "gallup.com", "url": "https://gallup.com/a", "title": "gallup.com"},
        {"index": 1, "domain": "facebook.com", "url": "https://facebook.com/a", "title": "facebook.com"},
        {"index": 2, "domain": "reuters.com", "url": "https://reuters.com/a", "title": "reuters.com"},
    ]
    supports = [
        {"grounding_chunk_indices": [0], "segment": {"start_index": 0, "end_index": 3, "text": "aaa"}},
        {"grounding_chunk_indices": [1], "segment": {"start_index": 4, "end_index": 7, "text": "bbb"}},
        {"grounding_chunk_indices": [1, 2], "segment": {"start_index": 8, "end_index": 11, "text": "ccc"}},
        {"grounding_chunk_indices": [1], "segment": {"start_index": 12, "end_index": 15, "text": "ddd"}},
    ]

    kept_chunks, kept_supports = filter_blocked_domain_grounding_alignment(
        chunks,
        supports,
        ["facebook.com"],
    )

    assert [c["index"] for c in kept_chunks] == [0, 2]
    # Support referencing only facebook (index 1) dropped; mixed [1,2] kept.
    assert [s["grounding_chunk_indices"] for s in kept_supports] == [[0], [1, 2]]

    raw = BackendRawResult(
        success=True,
        answer="answer",
        citations=[
            {"url": "https://gallup.com/a", "title": "g", "domain": "gallup.com", "snippet": ""},
            {"url": "https://facebook.com/a", "title": "f", "domain": "facebook.com", "snippet": ""},
            {"url": "https://reuters.com/a", "title": "r", "domain": "reuters.com", "snippet": ""},
        ],
        grounding_chunks=chunks,
        grounding_supports=supports,
        backend="gemini",
    )
    partial = normalize_grounding_result(raw, "gemini", blocked_domains=["facebook.com"])

    assert len(partial["results"]) == 2
    assert [c["index"] for c in partial["grounding_chunks"]] == [0, 2]
    assert [s["grounding_chunk_indices"] for s in partial["grounding_supports"]] == [[0], [1, 2]]
