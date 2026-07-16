"""P0-03: GroundingSearchBackend protocol and SearchCallParams."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from aiecs.tools.search_tool.backends.protocol import (
    BackendRawResult,
    GroundingSearchBackend,
    SearchCallParams,
)


class _FakeGroundingBackend:
    name = "fake"

    def is_configured(self) -> bool:
        return True

    def search(self, params: SearchCallParams) -> BackendRawResult:
        return BackendRawResult(
            success=True,
            answer="ok",
            citations=[{"url": "https://example.com", "title": "Example"}],
            backend=self.name,
            params_applied=["query"],
            params_ignored=["date_restrict"],
        )


def test_search_call_params_immutable() -> None:
    params = SearchCallParams(query="q", original_query="q", num_results=5)
    with pytest.raises(FrozenInstanceError):
        params.query = "other"  # type: ignore[misc]


def test_search_call_params_default_fields() -> None:
    params = SearchCallParams(query="enhanced", original_query="raw", num_results=10)
    assert params.start_index == 1
    assert params.language == "en"
    assert params.country == "us"
    assert params.safe_search == "medium"
    assert params.date_restrict is None
    assert params.file_type is None
    assert params.exclude_terms is None
    assert params.allowed_domains is None
    assert params.blocked_domains is None
    assert params.timeout_seconds == 30.0


def test_search_call_params_all_fields_set() -> None:
    params = SearchCallParams(
        query="enhanced query",
        original_query="raw query",
        num_results=7,
        start_index=11,
        language="zh-CN",
        country="cn",
        safe_search="high",
        date_restrict="m3",
        file_type="pdf",
        exclude_terms=["spam"],
        allowed_domains=["example.com"],
        blocked_domains=["facebook.com"],
        timeout_seconds=12.5,
    )
    assert params.query == "enhanced query"
    assert params.original_query == "raw query"
    assert params.num_results == 7
    assert params.start_index == 11
    assert params.language == "zh-CN"
    assert params.country == "cn"
    assert params.safe_search == "high"
    assert params.date_restrict == "m3"
    assert params.file_type == "pdf"
    assert params.exclude_terms == ["spam"]
    assert params.allowed_domains == ["example.com"]
    assert params.blocked_domains == ["facebook.com"]
    assert params.timeout_seconds == 12.5


def test_backend_raw_result_defaults() -> None:
    result = BackendRawResult(success=False)
    assert result.answer is None
    assert result.citations == []
    assert result.provider_native is None
    assert result.error is None
    assert result.error_type is None
    assert result.backend == ""
    assert result.params_applied == []
    assert result.params_ignored == []


def test_backend_raw_result_success_payload() -> None:
    native = {"groundingMetadata": {"webSearchQueries": ["test"]}}
    result = BackendRawResult(
        success=True,
        answer="summary",
        citations=[{"url": "https://a.test", "title": "A"}],
        provider_native=native,
        backend="gemini",
        params_applied=["query", "blocked_domains"],
        params_ignored=["date_restrict"],
    )
    assert result.success is True
    assert result.answer == "summary"
    assert len(result.citations) == 1
    assert result.provider_native == native
    assert result.backend == "gemini"
    assert result.params_applied == ["query", "blocked_domains"]
    assert result.params_ignored == ["date_restrict"]


def test_backend_raw_result_failure_fields() -> None:
    result = BackendRawResult(
        success=False,
        error="timeout",
        error_type="timeout",
        backend="grok",
    )
    assert result.success is False
    assert result.error == "timeout"
    assert result.error_type == "timeout"
    assert result.backend == "grok"
    assert result.citations == []


def test_grounding_search_backend_protocol_duck_typing() -> None:
    backend = _FakeGroundingBackend()
    assert isinstance(backend, GroundingSearchBackend)
    params = SearchCallParams(query="q", original_query="q", num_results=3)
    raw = backend.search(params)
    assert raw.success is True
    assert raw.backend == "fake"
    assert raw.params_ignored == ["date_restrict"]
