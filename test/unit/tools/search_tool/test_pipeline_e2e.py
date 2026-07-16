"""P4-04: Full pipeline e2e — intent → router → normalize → partition (§10)."""

from __future__ import annotations

import pytest

from aiecs.tools.search_tool.backends.protocol import BackendRawResult, SearchCallParams
from aiecs.tools.search_tool.backends.registry import GroundingBackendRegistry
from aiecs.tools.search_tool.core import SearchTool
from aiecs.tools.search_tool.resilience import BackendResilienceGuard
from test.unit.tools.search_tool.fakes import FakeGroundingBackend

TESLA_DEMOGRAPHIC_QUERY = "Why is Tesla popular among young people?"
COMMA_STACK_QUERY = (
    "criticisms of Tesla and Elon Musk affecting young people's popularity, "
    "Gen Z, Millennials, reports, articles"
)


class FakeCseBackend:
    name = "google_cse"

    def __init__(self, *, link: str = "https://cse.example/hit") -> None:
        self._link = link
        self.search_calls: list[SearchCallParams] = []
        self.resilience = BackendResilienceGuard(
            self.name,
            rate_limit_requests=100,
            rate_limit_window=86400,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=60,
        )

    def is_configured(self) -> bool:
        return True

    def search(self, params: SearchCallParams) -> BackendRawResult:
        self.search_calls.append(params)
        return BackendRawResult(
            success=True,
            backend=self.name,
            provider_native={
                "items": [
                    {
                        "title": "CSE Hit",
                        "link": self._link,
                        "snippet": "from cse",
                        "displayLink": "cse.example",
                    }
                ]
            },
        )


def _tesla_citations() -> list[dict]:
    return [
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
    ]


def _tool(backends: list, **config: object) -> SearchTool:
    base: dict[str, object] = {
        "grounding_provider": "auto",
        "grounding_provider_chain": "gemini,grok,google_cse",
        "enable_intent_analysis": True,
        "enable_quality_analysis": True,
        "enable_deduplication": False,
        "enable_context_tracking": False,
        "enable_intelligent_cache": False,
        "rewrite_before_grounding": True,
    }
    base.update(config)
    tool = SearchTool(config=base)
    registry = GroundingBackendRegistry()
    for backend in backends:
        registry.register(backend)
    tool._registry = registry
    return tool


@pytest.mark.gate_p4
def test_tesla_demographic_pipeline_after_partition() -> None:
    gemini = FakeGroundingBackend("gemini", citations=_tesla_citations())
    original = gemini.search

    def with_answer(params: SearchCallParams) -> BackendRawResult:
        result = original(params)
        result.answer = "Tesla Gen Z interest varies by survey."
        return result

    gemini.search = with_answer  # type: ignore[method-assign]
    tool = _tool(
        [
            gemini,
            FakeGroundingBackend("grok", configured=False),
            FakeGroundingBackend("google_cse", configured=False),
        ]
    )

    out = tool.search_web(TESLA_DEMOGRAPHIC_QUERY, num_results=5, auto_enhance=True)

    meta = out["_search_metadata"]
    assert meta["backend_used"] == "gemini"
    assert meta["partition_profile"] == "grounding"
    assert meta["intent_type"] == "demographic"
    assert meta["enhanced_query"] != TESLA_DEMOGRAPHIC_QUERY
    assert "survey" in meta["enhanced_query"].lower()
    assert out["grounding_answer"]
    assert out["results"]
    assert out["results"][0]["link"].startswith("https://")
    assert out["results"][0]["url"] == out["results"][0]["link"]
    assert out["results"][0]["_result_source"] == "grounding_citation"
    assert len(out["must_scrape_urls"]) >= 1
    must_urls = " ".join(item["url"] for item in out["must_scrape_urls"])
    primary_domains = " ".join(r.get("displayLink", "") for r in out["results"])
    assert "yougov.com" in must_urls or "yougov.com" in primary_domains
    low_domains = " ".join(r.get("displayLink", "") for r in out["low_signal"])
    assert "facebook.com" in low_domains
    assert out["_metadata"]["partition_profile"] == "grounding"


@pytest.mark.gate_p4
def test_comma_stack_rewrite_reaches_backend_query() -> None:
    gemini = FakeGroundingBackend("gemini", citations=_tesla_citations())
    tool = _tool(
        [
            gemini,
            FakeGroundingBackend("grok", configured=False),
            FakeGroundingBackend("google_cse", configured=False),
        ]
    )

    out = tool.search_web(COMMA_STACK_QUERY, num_results=5, auto_enhance=True)

    assert out["_search_metadata"]["intent_type"] == "demographic"
    assert out["_search_metadata"]["rewrite_applied"] is True
    enhanced = out["_search_metadata"]["enhanced_query"]
    assert enhanced != COMMA_STACK_QUERY
    assert "reports" not in enhanced.lower()
    assert "articles" not in enhanced.lower()
    assert gemini.search_calls
    assert gemini.search_calls[0].query == enhanced
    assert gemini.search_calls[0].original_query == COMMA_STACK_QUERY


@pytest.mark.gate_p4
def test_default_chain_gemini_fail_grok_success() -> None:
    grok = FakeGroundingBackend(
        "grok",
        citations=[
            {
                "url": "https://x.ai/news",
                "title": "xAI",
                "snippet": "ok",
                "domain": "x.ai",
            }
        ],
    )
    cse = FakeCseBackend()
    tool = _tool(
        [
            FakeGroundingBackend("gemini", succeed=False, error="gemini down"),
            grok,
            cse,
        ],
        enable_intent_analysis=False,
        enable_quality_analysis=False,
    )

    out = tool.search_web("chain walk", auto_enhance=False)
    assert out["_search_metadata"]["backend_used"] == "grok"
    assert out["_search_metadata"]["provider_chain"] == ["gemini", "grok"]
    assert len(cse.search_calls) == 0


@pytest.mark.gate_p4
def test_default_chain_gemini_grok_fail_cse_success() -> None:
    cse = FakeCseBackend(link="https://cse.example/fallback")
    tool = _tool(
        [
            FakeGroundingBackend("gemini", succeed=False, error="gemini down"),
            FakeGroundingBackend("grok", succeed=False, error="grok down"),
            cse,
        ],
        enable_intent_analysis=False,
        enable_quality_analysis=False,
    )

    out = tool.search_web("fall to cse", auto_enhance=False)
    assert out["_search_metadata"]["backend_used"] == "google_cse"
    assert out["_search_metadata"]["provider_chain"] == ["gemini", "grok", "google_cse"]
    assert out["_search_metadata"]["partition_profile"] == "cse"
    assert out["results"][0]["url"] == "https://cse.example/fallback"
    assert len(cse.search_calls) == 1


@pytest.mark.gate_p4
def test_search_batch_pipeline_pins_grok_after_gemini_fail() -> None:
    grok = FakeGroundingBackend(
        "grok",
        citations=[
            {
                "url": "https://grok.example/a",
                "title": "A",
                "snippet": "ok",
                "domain": "grok.example",
            }
        ],
    )
    tool = _tool(
        [
            FakeGroundingBackend("gemini", succeed=False, error="down"),
            grok,
            FakeGroundingBackend("google_cse", configured=False),
        ],
        enable_intent_analysis=False,
        enable_quality_analysis=False,
        batch_routing_mode="pin_on_first_success",
    )

    out = tool.search_batch(
        queries=["q1 about alpha", "q2 about beta", "q3 about gamma"],
        num_results=3,
        auto_enhance=False,
    )

    assert out["_metadata"]["batch_pinned_backend"] == "grok"
    assert out["_metadata"]["per_query_backend_used"] == ["grok", "grok", "grok"]
    assert len(grok.search_calls) == 3
    assert all(bucket.get("success") is not False for bucket in out["per_query"])
    assert out["per_query"][0]["_search_metadata"]["backend_used"] == "grok"


@pytest.mark.gate_p4
def test_clear_search_cache_forces_remiss() -> None:
    fake = FakeGroundingBackend(
        "gemini",
        citations=[
            {
                "url": "https://gemini.example/1",
                "title": "one",
                "snippet": "ok",
                "domain": "gemini.example",
            }
        ],
    )
    tool = _tool(
        [
            fake,
            FakeGroundingBackend("grok", configured=False),
            FakeGroundingBackend("google_cse", configured=False),
        ],
        enable_intent_analysis=False,
        enable_quality_analysis=False,
    )
    tool._executor.config.enable_cache = True

    tool.search_web("cache purge query", auto_enhance=False)
    tool.search_web("cache purge query", auto_enhance=False)
    assert len(fake.search_calls) == 1

    tool.clear_search_cache()
    tool.search_web("cache purge query", auto_enhance=False)
    assert len(fake.search_calls) == 2
