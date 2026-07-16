"""P0-05: CredentialResolver skeleton with opt-in LLM fallback gate."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from aiecs.tools.search_tool.backends.credentials import (
    CredentialResolver,
    log_fallback_warning_once,
    reset_fallback_warning_state_for_tests,
)
from aiecs.tools.search_tool.core import SearchTool


@pytest.fixture(autouse=True)
def _reset_fallback_warnings() -> None:
    reset_fallback_warning_state_for_tests()


def _llm_settings_with_googleai_key() -> SimpleNamespace:
    return SimpleNamespace(
        googleai_api_key="llm-googleai-key",
        xai_api_key="",
        grok_api_key="",
        vertex_project_id="",
        vertex_project_id_maas="",
        google_application_credentials="",
        google_application_credentials_vertex_gemini="",
        google_application_credentials_vertex_maas="",
        maas_vertex_project_id="",
    )


@pytest.mark.gate_p0
def test_gemini_not_configured_when_llm_key_only_and_fallback_false() -> None:
    settings_loader = MagicMock(return_value=_llm_settings_with_googleai_key())
    config = SearchTool.Config.model_construct(allow_llm_credential_fallback=False)
    resolver = CredentialResolver(config, settings_loader=settings_loader)

    assert resolver.resolve_gemini_auth_mode() is None
    settings_loader.assert_not_called()


@pytest.mark.gate_p0
def test_gemini_googleai_resolved_with_llm_fallback_and_warning_once(caplog: pytest.LogCaptureFixture) -> None:
    settings_loader = MagicMock(return_value=_llm_settings_with_googleai_key())
    config = SearchTool.Config.model_construct(allow_llm_credential_fallback=True)
    resolver = CredentialResolver(config, settings_loader=settings_loader)

    with caplog.at_level("WARNING"):
        assert resolver.resolve_gemini_auth_mode() == "googleai"
        assert resolver.resolve_gemini_auth_mode() == "googleai"

    settings_loader.assert_called_once()
    fallback_warnings = [r for r in caplog.records if "LLM Settings fallback for gemini" in r.message]
    assert len(fallback_warnings) == 1


@pytest.mark.gate_p0
def test_search_tool_gemini_key_takes_precedence_without_llm_fallback() -> None:
    settings_loader = MagicMock(return_value=_llm_settings_with_googleai_key())
    config = SearchTool.Config.model_construct(
        allow_llm_credential_fallback=False,
    )
    object.__setattr__(config, "gemini_api_key", "search-tool-gemini-key")
    resolver = CredentialResolver(config, settings_loader=settings_loader)

    assert resolver.resolve_gemini_auth_mode() == "googleai"
    settings_loader.assert_not_called()


@pytest.mark.gate_p0
def test_grok_not_configured_when_llm_key_only_and_fallback_false() -> None:
    settings = _llm_settings_with_googleai_key()
    settings.xai_api_key = "llm-xai-key"
    settings_loader = MagicMock(return_value=settings)
    config = SearchTool.Config.model_construct(allow_llm_credential_fallback=False)
    resolver = CredentialResolver(config, settings_loader=settings_loader)

    assert resolver.resolve_grok_auth_mode() is None
    settings_loader.assert_not_called()


@pytest.mark.gate_p0
def test_grok_xai_resolved_with_llm_fallback() -> None:
    settings = _llm_settings_with_googleai_key()
    settings.xai_api_key = "llm-xai-key"
    settings_loader = MagicMock(return_value=settings)
    config = SearchTool.Config.model_construct(allow_llm_credential_fallback=True)
    resolver = CredentialResolver(config, settings_loader=settings_loader)

    assert resolver.resolve_grok_auth_mode() == "xai"
    settings_loader.assert_called_once()


@pytest.mark.gate_p0
def test_log_fallback_warning_once_dedupes_per_backend(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING"):
        log_fallback_warning_once("gemini")
        log_fallback_warning_once("gemini")
        log_fallback_warning_once("grok")

    gemini_warnings = [r for r in caplog.records if "fallback for gemini" in r.message]
    grok_warnings = [r for r in caplog.records if "fallback for grok" in r.message]
    assert len(gemini_warnings) == 1
    assert len(grok_warnings) == 1


@pytest.mark.gate_p1
def test_credential_source_search_tool_when_gemini_key_present() -> None:
    config = SearchTool.Config.model_construct(
        allow_llm_credential_fallback=True,
        gemini_api_key="search-tool-gemini-key",
    )
    settings_loader = MagicMock(return_value=_llm_settings_with_googleai_key())
    resolver = CredentialResolver(config, settings_loader=settings_loader)

    assert resolver.resolve_credential_source("gemini") == "search_tool"
    settings_loader.assert_not_called()


@pytest.mark.gate_p1
def test_credential_source_llm_fallback_when_only_llm_gemini_key() -> None:
    config = SearchTool.Config.model_construct(allow_llm_credential_fallback=True)
    settings_loader = MagicMock(return_value=_llm_settings_with_googleai_key())
    resolver = CredentialResolver(config, settings_loader=settings_loader)

    assert resolver.resolve_credential_source("gemini") == "llm_fallback"
    settings_loader.assert_called_once()


@pytest.mark.gate_p1
def test_credential_source_none_when_fallback_disabled_and_no_search_tool_key() -> None:
    config = SearchTool.Config.model_construct(allow_llm_credential_fallback=False)
    settings_loader = MagicMock(return_value=_llm_settings_with_googleai_key())
    resolver = CredentialResolver(config, settings_loader=settings_loader)

    assert resolver.resolve_credential_source("gemini") is None
    settings_loader.assert_not_called()


@pytest.mark.gate_p1
def test_search_web_emits_credential_source_search_tool() -> None:
    from aiecs.tools.search_tool.backends.registry import GroundingBackendRegistry
    from test.unit.tools.search_tool.fakes import FakeGroundingBackend

    tool = SearchTool(
        config={
            "grounding_provider": "gemini",
            "gemini_api_key": "search-tool-gemini-key",
            "gemini_grounding_auth": "googleai",
            "enable_intent_analysis": False,
            "enable_quality_analysis": False,
            "enable_intelligent_cache": False,
            "enable_context_tracking": False,
            "enable_deduplication": False,
        }
    )
    registry = GroundingBackendRegistry()
    registry.register(
        FakeGroundingBackend(
            "gemini",
            citations=[
                {
                    "url": "https://example.com/a",
                    "title": "A",
                    "snippet": "ok",
                    "domain": "example.com",
                }
            ],
        )
    )
    tool._registry = registry

    out = tool.search_web("billing isolation query", auto_enhance=False)

    assert out["_search_metadata"]["backend_used"] == "gemini"
    assert out["_search_metadata"]["credential_source"] == "search_tool"


@pytest.mark.gate_p1
def test_search_web_emits_credential_source_llm_fallback() -> None:
    from aiecs.tools.search_tool.backends.gemini_grounding import GeminiGroundingBackend
    from aiecs.tools.search_tool.backends.registry import GroundingBackendRegistry
    from test.unit.tools.search_tool.fakes import FakeGroundingBackend

    config = {
        "grounding_provider": "gemini",
        "gemini_grounding_auth": "googleai",
        "allow_llm_credential_fallback": True,
        "enable_intent_analysis": False,
        "enable_quality_analysis": False,
        "enable_intelligent_cache": False,
        "enable_context_tracking": False,
        "enable_deduplication": False,
    }
    tool = SearchTool(config=config)
    resolver = CredentialResolver(
        tool.config,
        settings_loader=lambda: _llm_settings_with_googleai_key(),
    )
    tool._credential_resolver = resolver

    # Fake success path; credential_source comes from resolver (llm fallback).
    registry = GroundingBackendRegistry()
    registry.register(
        FakeGroundingBackend(
            "gemini",
            citations=[
                {
                    "url": "https://example.com/b",
                    "title": "B",
                    "snippet": "ok",
                    "domain": "example.com",
                }
            ],
        )
    )
    tool._registry = registry

    # Ensure live GeminiGroundingBackend would also see fallback (parity).
    assert GeminiGroundingBackend(tool.config, credential_resolver=resolver).is_configured()

    out = tool.search_web("fallback audit query", auto_enhance=False)

    assert out["_search_metadata"]["credential_source"] == "llm_fallback"
