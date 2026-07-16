"""P4-03: Routing cache fingerprint isolation (§3.2)."""

from __future__ import annotations

import pytest

from aiecs.tools.search_tool.backends.protocol import BackendRawResult, SearchCallParams
from aiecs.tools.search_tool.backends.registry import GroundingBackendRegistry
from aiecs.tools.search_tool.cache_fingerprint import (
    CACHE_SCHEMA_VERSION,
    build_routing_cache_fingerprint,
)
from aiecs.tools.search_tool.core import SearchTool
from aiecs.tools.search_tool.resilience import BackendResilienceGuard
from test.unit.tools.search_tool.fakes import FakeGroundingBackend


def _config(**overrides: object) -> SearchTool.Config:
    base = {
        "grounding_provider": "auto",
        "grounding_provider_chain": "gemini,grok,google_cse",
        "gemini_grounding_auth": "auto",
        "grok_grounding_auth": "auto",
        "grok_maas_web_search_enabled": False,
        "rewrite_before_grounding": True,
        "batch_routing_mode": "pin_on_first_success",
        "search_error_mode": "auto",
        "cache_schema_version": CACHE_SCHEMA_VERSION,
    }
    base.update(overrides)
    return SearchTool.Config.model_construct(**base)


class FakeCseBackend:
    """Minimal CSE-shaped backend returning provider_native.items."""

    name = "google_cse"

    def __init__(self, *, link: str = "https://cse.example/old") -> None:
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
                        "title": "CSE old",
                        "link": self._link,
                        "snippet": "cached era",
                        "displayLink": "cse.example",
                    }
                ]
            },
        )


def _base_tool_config(**overrides: object) -> dict[str, object]:
    cfg: dict[str, object] = {
        "grounding_provider": "auto",
        "grounding_provider_chain": "gemini,grok,google_cse",
        "enable_intent_analysis": False,
        "enable_context_tracking": False,
        "enable_intelligent_cache": False,
        "enable_quality_analysis": False,
        "enable_deduplication": False,
    }
    cfg.update(overrides)
    return cfg


def _tool_with_backends(
    backends: list,
    **config_overrides: object,
) -> SearchTool:
    tool = SearchTool(config=_base_tool_config(**config_overrides))
    # Executor cache is on by default; keep it explicit for fingerprint tests.
    tool._executor.config.enable_cache = True
    registry = GroundingBackendRegistry()
    for backend in backends:
        registry.register(backend)
    tool._registry = registry
    return tool


@pytest.mark.gate_p4
def test_partition_tuning_knobs_change_fingerprint() -> None:
    base = _config()
    fp_default = build_routing_cache_fingerprint(base)
    fp_trust_off = build_routing_cache_fingerprint(
        _config(grounding_trust_citations=False)
    )
    fp_threshold = build_routing_cache_fingerprint(
        _config(grounding_relevance_threshold=0.7)
    )
    fp_sparse = build_routing_cache_fingerprint(
        _config(grounding_sparse_snippet_max_len=40)
    )
    fp_top_k = build_routing_cache_fingerprint(_config(grounding_citation_trust_top_k=5))
    fp_min_scrape = build_routing_cache_fingerprint(_config(grounding_min_must_scrape=2))

    assert fp_default != fp_trust_off
    assert fp_default != fp_threshold
    assert fp_default != fp_sparse
    assert fp_default != fp_top_k
    assert fp_default != fp_min_scrape
    assert "grounding_trust_citations" in fp_default
    assert "grounding_relevance_threshold" in fp_default


@pytest.mark.gate_p4
def test_same_query_partition_knob_change_cache_miss() -> None:
    fake = FakeGroundingBackend(
        "gemini",
        citations=[
            {
                "url": "https://gemini.example/stable",
                "title": "stable",
                "snippet": "ok",
                "domain": "gemini.example",
            }
        ],
    )
    tool = _tool_with_backends(
        [
            fake,
            FakeGroundingBackend("grok", configured=False),
            FakeGroundingBackend("google_cse", configured=False),
        ],
        grounding_relevance_threshold=0.5,
    )

    first = tool.search_web("partition knob query", auto_enhance=False)
    assert len(fake.search_calls) == 1
    tool.search_web("partition knob query", auto_enhance=False)
    assert len(fake.search_calls) == 1  # cache hit

    tool.config = tool.config.model_copy(update={"grounding_relevance_threshold": 0.7})
    second = tool.search_web("partition knob query", auto_enhance=False)
    assert len(fake.search_calls) == 2  # fingerprint miss after partition tune
    assert first["results"][0]["url"] == second["results"][0]["url"]


@pytest.mark.gate_p4
def test_google_vs_google_cse_chain_same_fingerprint() -> None:
    cfg = _config()
    fp_alias = build_routing_cache_fingerprint(
        cfg,
        overrides={"grounding_provider_chain": "gemini,grok,google"},
    )
    fp_canonical = build_routing_cache_fingerprint(
        cfg,
        overrides={"grounding_provider_chain": "gemini,grok,google_cse"},
    )
    assert fp_alias == fp_canonical
    assert CACHE_SCHEMA_VERSION in fp_alias


@pytest.mark.gate_p4
def test_same_query_different_chain_cache_miss() -> None:
    fake_gemini = FakeGroundingBackend(
        "gemini",
        citations=[
            {
                "url": "https://gemini.example/hit",
                "title": "gemini hit",
                "snippet": "ok",
                "domain": "gemini.example",
            }
        ],
    )
    tool = _tool_with_backends(
        [
            fake_gemini,
            FakeGroundingBackend("grok", configured=False),
            FakeGroundingBackend("google_cse", configured=False),
        ],
        grounding_provider_chain="gemini,google_cse",
    )

    result1 = tool.search_web("tesla survey", auto_enhance=False)
    assert result1["_search_metadata"]["backend_used"] == "gemini"
    assert len(fake_gemini.search_calls) == 1

    fake_grok = FakeGroundingBackend(
        "grok",
        citations=[
            {
                "url": "https://grok.example/hit",
                "title": "grok hit",
                "snippet": "ok",
                "domain": "grok.example",
            }
        ],
    )
    tool.config = tool.config.model_copy(update={"grounding_provider_chain": "grok,google_cse"})
    tool._registry = GroundingBackendRegistry()
    tool._registry.register(FakeGroundingBackend("gemini", configured=False))
    tool._registry.register(fake_grok)
    tool._registry.register(FakeGroundingBackend("google_cse", configured=False))

    result2 = tool.search_web("tesla survey", auto_enhance=False)
    assert result2["_search_metadata"]["backend_used"] == "grok"
    assert len(fake_grok.search_calls) == 1
    assert result1["results"][0]["url"] != result2["results"][0]["url"]


@pytest.mark.gate_p4
def test_preseeded_cse_cache_not_returned_when_grounding_active() -> None:
    cse = FakeCseBackend(link="https://cse.example/old")
    tool = _tool_with_backends(
        [cse],
        grounding_provider="google_cse",
        grounding_provider_chain="google_cse",
    )

    cse_result = tool.search_web("shared query", auto_enhance=False)
    assert cse_result["_search_metadata"]["backend_used"] == "google_cse"
    assert cse_result["results"][0]["url"] == "https://cse.example/old"

    gemini = FakeGroundingBackend(
        "gemini",
        citations=[
            {
                "url": "https://gemini.example/fresh",
                "title": "Gemini fresh",
                "snippet": "new",
                "domain": "gemini.example",
            }
        ],
    )
    tool.config = tool.config.model_copy(
        update={
            "grounding_provider": "auto",
            "grounding_provider_chain": "gemini,grok,google_cse",
        }
    )
    tool._registry = GroundingBackendRegistry()
    tool._registry.register(gemini)
    tool._registry.register(FakeGroundingBackend("grok", configured=False))
    tool._registry.register(FakeGroundingBackend("google_cse", configured=False))

    grounded = tool.search_web("shared query", auto_enhance=False)
    assert grounded["_search_metadata"]["backend_used"] == "gemini"
    assert grounded["results"][0]["url"] == "https://gemini.example/fresh"
    assert len(gemini.search_calls) == 1


@pytest.mark.gate_p4
def test_same_query_same_fingerprint_cache_hit() -> None:
    fake = FakeGroundingBackend(
        "gemini",
        citations=[
            {
                "url": "https://gemini.example/stable",
                "title": "stable",
                "snippet": "ok",
                "domain": "gemini.example",
            }
        ],
    )
    tool = _tool_with_backends(
        [
            fake,
            FakeGroundingBackend("grok", configured=False),
            FakeGroundingBackend("google_cse", configured=False),
        ]
    )
    first = tool.search_web("stable query", auto_enhance=False)
    second = tool.search_web("stable query", auto_enhance=False)
    assert first["results"][0]["url"] == second["results"][0]["url"]
    assert len(fake.search_calls) == 1


@pytest.mark.gate_p4
def test_tier_c_failure_not_cached() -> None:
    failing = FakeGroundingBackend("gemini", succeed=False, error="down")
    tool = _tool_with_backends(
        [
            failing,
            FakeGroundingBackend("grok", configured=False),
            FakeGroundingBackend("google_cse", configured=False),
        ],
        search_error_mode="return_dict",
    )

    first = tool.search_web("fail query", auto_enhance=False)
    assert first.get("success") is False
    calls_after_first = len(failing.search_calls)

    second = tool.search_web("fail query", auto_enhance=False)
    assert second.get("success") is False
    assert len(failing.search_calls) == calls_after_first + 1
