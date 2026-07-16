"""P0-04: GroundingBackendRegistry skeleton and backend name aliases."""

from __future__ import annotations

import pytest

from aiecs.tools.search_tool.backends.protocol import BackendRawResult, SearchCallParams
from aiecs.tools.search_tool.backends.registry import (
    GroundingBackendRegistry,
    normalize_backend_name,
    normalize_provider_chain,
)
from aiecs.tools.search_tool.constants import ValidationError


class _FakeBackend:
    def __init__(self, name: str, *, configured: bool = True) -> None:
        self.name = name
        self._configured = configured

    def is_configured(self) -> bool:
        return self._configured

    def search(self, params: SearchCallParams) -> BackendRawResult:
        return BackendRawResult(success=True, backend=self.name)


@pytest.mark.gate_p0
def test_normalize_google_to_google_cse() -> None:
    assert normalize_backend_name("google") == "google_cse"
    assert normalize_backend_name("  GOOGLE  ") == "google_cse"


@pytest.mark.gate_p0
def test_normalize_cse_to_google_cse() -> None:
    assert normalize_backend_name("cse") == "google_cse"
    assert normalize_backend_name("google_cse") == "google_cse"


@pytest.mark.gate_p0
def test_normalize_provider_chain_google_alias_equivalent() -> None:
    chain_a = normalize_provider_chain("gemini,grok,google")
    chain_b = normalize_provider_chain("gemini,grok,google_cse")
    assert chain_a == ["gemini", "grok", "google_cse"]
    assert chain_b == ["gemini", "grok", "google_cse"]


@pytest.mark.gate_p0
def test_unknown_custom_name_passthrough_unchanged() -> None:
    assert normalize_backend_name("Exa") == "Exa"
    assert normalize_backend_name("exa") == "exa"


@pytest.mark.gate_p0
def test_validate_forced_unknown_builtin_raises_validation_error() -> None:
    registry = GroundingBackendRegistry()
    with pytest.raises(ValidationError, match="Canonical built-in names: gemini, grok, google_cse"):
        registry.validate_forced_backend_name("goog")


@pytest.mark.gate_p0
def test_validate_forced_registered_custom_backend() -> None:
    registry = GroundingBackendRegistry()
    registry.register(_FakeBackend("exa"))
    assert registry.validate_forced_backend_name("exa") == "exa"


@pytest.mark.gate_p0
def test_registry_register_get_list_names() -> None:
    registry = GroundingBackendRegistry()
    registry.register(_FakeBackend("gemini"))
    registry.register(_FakeBackend("google_cse"))

    assert registry.get("google") is not None
    assert registry.get("google").name == "google_cse"  # type: ignore[union-attr]
    assert registry.list_names() == ["gemini", "google_cse"]


@pytest.mark.gate_p0
def test_has_configured_backend_stub() -> None:
    registry = GroundingBackendRegistry()
    assert registry.has_configured_backend() is False

    registry.register(_FakeBackend("gemini", configured=False))
    assert registry.has_configured_backend() is False

    registry.register(_FakeBackend("grok", configured=True))
    assert registry.has_configured_backend() is True
