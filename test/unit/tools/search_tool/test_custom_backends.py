"""P5-01: SearchTool custom_grounding_backends registration (§8 / §9.4)."""

from __future__ import annotations

import json

import pytest

from aiecs.tools.search_tool.backends.async_bridge import run_async_from_sync
from aiecs.tools.search_tool.core import SearchTool
from test.unit.tools.search_tool.fakes import FakeGroundingBackend


def _base_config(**overrides: object) -> dict[str, object]:
    cfg: dict[str, object] = {
        "grounding_provider": "auto",
        "grounding_provider_chain": "exa,gemini,grok,google_cse",
        "enable_intent_analysis": False,
        "enable_context_tracking": False,
        "enable_intelligent_cache": False,
        "enable_quality_analysis": False,
        "enable_deduplication": False,
        "rewrite_before_grounding": False,
    }
    cfg.update(overrides)
    return cfg


@pytest.mark.gate_p5
def test_custom_exa_backend_routable_when_chain_includes_exa() -> None:
    exa = FakeGroundingBackend(
        "exa",
        citations=[
            {
                "url": "https://exa.example/hit",
                "title": "exa hit",
                "snippet": "ok",
                "domain": "exa.example",
            }
        ],
    )
    tool = SearchTool(
        config=_base_config(),
        custom_grounding_backends=[exa],
    )

    assert tool._registry.get("exa") is exa
    assert "exa" in tool._registry.list_names()
    # Neutralize built-ins so env credentials cannot steal the route.
    tool._registry.register(FakeGroundingBackend("gemini", configured=False))
    tool._registry.register(FakeGroundingBackend("grok", configured=False))
    tool._registry.register(FakeGroundingBackend("google_cse", configured=False))

    out = tool.search_web("exa query", auto_enhance=False)

    assert out["_search_metadata"]["backend_used"] == "exa"
    assert len(exa.search_calls) == 1
    assert out["results"][0]["url"] == "https://exa.example/hit"


@pytest.mark.gate_p5
def test_custom_backend_appears_in_fingerprint_cache_miss_vs_without() -> None:
    citations = [
        {
            "url": "https://gemini.example/shared",
            "title": "shared",
            "snippet": "ok",
            "domain": "gemini.example",
        }
    ]
    gemini_plain = FakeGroundingBackend("gemini", citations=citations)
    tool_plain = SearchTool(
        config=_base_config(
            grounding_provider_chain="gemini,google_cse",
        ),
    )
    tool_plain._executor.config.enable_cache = True
    # Keep CSE path off; force gemini fake for deterministic cache body.
    tool_plain._registry.register(gemini_plain)
    tool_plain._registry.register(FakeGroundingBackend("grok", configured=False))
    tool_plain._registry.register(FakeGroundingBackend("google_cse", configured=False))

    fp_plain = tool_plain._routing_cache_fingerprint()
    payload_plain = json.loads(fp_plain)
    assert payload_plain["custom_backend_names"] == []

    first = tool_plain.search_web("shared query", auto_enhance=False)
    assert first["_search_metadata"]["backend_used"] == "gemini"
    assert len(gemini_plain.search_calls) == 1

    exa = FakeGroundingBackend(
        "exa",
        citations=[
            {
                "url": "https://exa.example/fresh",
                "title": "exa fresh",
                "snippet": "new",
                "domain": "exa.example",
            }
        ],
    )
    gemini_custom = FakeGroundingBackend("gemini", citations=citations)
    tool_custom = SearchTool(
        config=_base_config(
            grounding_provider_chain="exa,gemini,google_cse",
        ),
        custom_grounding_backends=[exa],
    )
    tool_custom._executor.config.enable_cache = True
    tool_custom._registry.register(gemini_custom)
    tool_custom._registry.register(FakeGroundingBackend("grok", configured=False))
    tool_custom._registry.register(FakeGroundingBackend("google_cse", configured=False))

    fp_custom = tool_custom._routing_cache_fingerprint()
    payload_custom = json.loads(fp_custom)
    assert payload_custom["custom_backend_names"] == ["exa"]
    assert fp_custom != fp_plain

    # Same query + different fingerprint must not reuse plain-tool cache semantics:
    # exercise miss on a single instance by registering custom after a hit.
    gemini_same = FakeGroundingBackend("gemini", citations=citations)
    tool = SearchTool(
        config=_base_config(grounding_provider_chain="gemini,google_cse"),
    )
    tool._executor.config.enable_cache = True
    tool._registry.register(gemini_same)
    tool._registry.register(FakeGroundingBackend("grok", configured=False))
    tool._registry.register(FakeGroundingBackend("google_cse", configured=False))

    hit1 = tool.search_web("shared query", auto_enhance=False)
    assert len(gemini_same.search_calls) == 1
    hit2 = tool.search_web("shared query", auto_enhance=False)
    assert len(gemini_same.search_calls) == 1  # cache hit
    assert hit1["results"][0]["url"] == hit2["results"][0]["url"]

    exa2 = FakeGroundingBackend(
        "exa",
        citations=[
            {
                "url": "https://exa.example/after-register",
                "title": "exa after",
                "snippet": "new",
                "domain": "exa.example",
            }
        ],
    )
    tool._registry.register(exa2)
    tool.config = tool.config.model_copy(
        update={"grounding_provider_chain": "exa,gemini,google_cse"}
    )
    assert "exa" in json.loads(tool._routing_cache_fingerprint())["custom_backend_names"]

    after = tool.search_web("shared query", auto_enhance=False)
    assert after["_search_metadata"]["backend_used"] == "exa"
    assert len(exa2.search_calls) == 1
    assert after["results"][0]["url"] == "https://exa.example/after-register"


@pytest.mark.gate_p5
def test_async_bridge_runs_coro_without_running_loop() -> None:
    async def _one() -> int:
        return 42

    assert run_async_from_sync(_one(), timeout=5.0) == 42
