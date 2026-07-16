"""P4-02: Backend-aware grounding partition (§3.3)."""

from __future__ import annotations

import pytest

from aiecs.tools.search_tool.analyzers import ResultQualityAnalyzer, partition_search_results as cse_partition
from aiecs.tools.search_tool.backends.registry import GroundingBackendRegistry
from aiecs.tools.search_tool.core import SearchTool
from aiecs.tools.search_tool.normalizer import normalize_grounding_result
from aiecs.tools.search_tool.partition import (
    partition_search_results,
    resolve_partition_profile,
)
from aiecs.tools.search_tool.backends.protocol import BackendRawResult
from test.unit.tools.search_tool.fakes import FakeGroundingBackend


def _tesla_grounding_results() -> list[dict]:
    raw = BackendRawResult(
        success=True,
        answer="Tesla Gen Z interest is mixed across surveys.",
        citations=[
            {
                "url": "https://www.yougov.com/topics/automotive/articles-reports/tesla-gen-z",
                "title": "YouGov Tesla Gen Z brand survey",
                "domain": "www.yougov.com",
                "snippet": "",
            },
            {
                "url": "https://www.facebook.com/groups/teslafans",
                "title": "Tesla fans",
                "domain": "www.facebook.com",
                "snippet": "",
            },
            {
                "url": "https://www.pewresearch.org/internet/tesla-ev",
                "title": "EV ownership demographics",
                "domain": "www.pewresearch.org",
                "snippet": "short",
            },
        ],
        backend="gemini",
    )
    return normalize_grounding_result(raw, "gemini")["results"]


@pytest.mark.gate_p4
def test_resolve_partition_profile_mapping() -> None:
    assert resolve_partition_profile("google_cse") == "cse"
    assert resolve_partition_profile("gemini") == "grounding"
    assert resolve_partition_profile("grok") == "grounding"
    assert resolve_partition_profile("exa") == "grounding"
    assert resolve_partition_profile("gemini", grounding_trust_citations=False) == "cse"


@pytest.mark.gate_p4
def test_tesla_demographic_grounding_partition_must_scrape() -> None:
    analyzer = ResultQualityAnalyzer()
    results = _tesla_grounding_results()
    citations = [r["link"] for r in results]

    primary, low_signal, must_scrape = partition_search_results(
        analyzer,
        results,
        num_results=5,
        partition_profile="grounding",
        query="Tesla Gen Z Millennials popularity survey",
        intent_type="demographic",
        grounding_citations=citations,
        grounding_relevance_threshold=0.5,
        grounding_sparse_snippet_max_len=80,
        grounding_citation_trust_top_k=3,
        grounding_min_must_scrape=1,
    )

    primary_domains = {r.get("displayLink", "") for r in primary}
    low_domains = {r.get("displayLink", "") for r in low_signal}
    must_urls = " ".join(item["url"] for item in must_scrape)

    assert any("yougov.com" in d for d in primary_domains) or "yougov.com" in must_urls
    assert any("facebook.com" in d for d in low_domains)
    assert len(must_scrape) >= 1
    assert "yougov.com" in must_urls or "pewresearch.org" in must_urls


@pytest.mark.gate_p4
def test_grounding_empty_snippets_non_social_promotes_primary() -> None:
    analyzer = ResultQualityAnalyzer()
    raw = BackendRawResult(
        success=True,
        citations=[
            {
                "url": "https://statista.com/statistics/tesla",
                "title": "Tesla stats",
                "domain": "statista.com",
                "snippet": "",
            },
            {
                "url": "https://kpmg.com/ev-report",
                "title": "EV report",
                "domain": "kpmg.com",
                "snippet": "",
            },
            {
                "url": "https://example.org/notes",
                "title": "Notes",
                "domain": "example.org",
                "snippet": "",
            },
        ],
        backend="grok",
    )
    results = normalize_grounding_result(raw, "grok")["results"]

    primary, _low, must_scrape = partition_search_results(
        analyzer,
        results,
        num_results=3,
        partition_profile="grounding",
        query="Tesla EV adoption",
        intent_type="causal",
        grounding_citations=[r["link"] for r in results],
    )

    assert len(primary) >= 1
    assert len(must_scrape) >= 1


@pytest.mark.gate_p4
def test_partition_profile_cse_demotes_social_noise_unchanged() -> None:
    """Regression: CSE profile matches analyzers.partition_search_results."""
    analyzer = ResultQualityAnalyzer()
    query = "Tesla Gen Z Millennials popularity survey"

    def build(domain: str, title: str, position: int) -> dict:
        result = {
            "title": title,
            "link": f"https://{domain}/page",
            "snippet": title,
            "displayLink": domain,
            "metadata": {},
        }
        quality = analyzer.analyze_result_quality(result, query, position)
        result["_quality"] = quality
        result["_quality_summary"] = {
            "score": quality["quality_score"],
            "level": quality["credibility_level"],
            "is_authoritative": quality["authority_score"] > 0.8,
            "is_relevant": quality["relevance_score"] > 0.7,
            "is_fresh": quality["freshness_score"] > 0.7,
            "warnings_count": len(quality["warnings"]),
        }
        return result

    results = [
        build("facebook.com", "Tesla fans", 1),
        build("reddit.com", "Tesla thread", 2),
        build("yougov.com", "Tesla brand survey Gen Z", 3),
    ]

    via_dispatch = partition_search_results(
        analyzer, results, num_results=2, partition_profile="cse"
    )
    via_cse = cse_partition(analyzer, results, num_results=2)

    assert [r["displayLink"] for r in via_dispatch[0]] == [r["displayLink"] for r in via_cse[0]]
    assert {r["displayLink"] for r in via_dispatch[1]} == {r["displayLink"] for r in via_cse[1]}
    assert via_dispatch[0][0]["displayLink"] == "yougov.com"
    assert {r["displayLink"] for r in via_dispatch[1]} == {"facebook.com", "reddit.com"}


@pytest.mark.gate_p4
def test_grounding_only_social_may_have_empty_must_scrape() -> None:
    analyzer = ResultQualityAnalyzer()
    raw = BackendRawResult(
        success=True,
        citations=[
            {
                "url": "https://www.facebook.com/a",
                "title": "fb",
                "domain": "www.facebook.com",
                "snippet": "",
            },
            {
                "url": "https://www.reddit.com/r/tesla",
                "title": "reddit",
                "domain": "www.reddit.com",
                "snippet": "",
            },
        ],
        backend="gemini",
    )
    results = normalize_grounding_result(raw, "gemini")["results"]
    primary, low_signal, must_scrape = partition_search_results(
        analyzer,
        results,
        num_results=5,
        partition_profile="grounding",
        query="Tesla chatter",
        intent_type="general",
        grounding_citations=[r["link"] for r in results],
        grounding_min_must_scrape=1,
    )

    assert len(primary) == 0
    assert len(low_signal) == 2
    assert must_scrape == []


@pytest.mark.gate_p4
def test_search_web_sets_partition_profile_metadata() -> None:
    tool = SearchTool(
        config={
            "enable_intent_analysis": False,
            "enable_context_tracking": False,
            "enable_intelligent_cache": False,
            "enable_quality_analysis": True,
            "enable_deduplication": False,
            "grounding_provider": "auto",
        }
    )
    gemini = FakeGroundingBackend(
        "gemini",
        citations=[
            {
                "url": "https://www.yougov.com/tesla",
                "title": "YouGov Tesla Gen Z survey",
                "snippet": "",
                "domain": "www.yougov.com",
            },
            {
                "url": "https://www.facebook.com/tesla",
                "title": "Facebook",
                "snippet": "",
                "domain": "www.facebook.com",
            },
        ],
    )
    original = gemini.search

    def search_with_answer(params):
        result = original(params)
        result.answer = "grounded"
        return result

    gemini.search = search_with_answer  # type: ignore[method-assign]

    registry = GroundingBackendRegistry()
    registry.register(gemini)
    registry.register(FakeGroundingBackend("grok", configured=False))
    registry.register(FakeGroundingBackend("google_cse", configured=False))
    tool._registry = registry

    out = tool.search_web(
        "Tesla Gen Z Millennials popularity survey",
        num_results=5,
        auto_enhance=False,
    )

    assert out["_search_metadata"]["partition_profile"] == "grounding"
    assert out["_metadata"]["partition_profile"] == "grounding"
    assert len(out["must_scrape_urls"]) >= 1
    low_domains = " ".join(r.get("displayLink", "") for r in out["low_signal"])
    assert "facebook.com" in low_domains
