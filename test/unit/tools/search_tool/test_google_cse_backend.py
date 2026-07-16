"""P1-02: GoogleCseBackend CSE param mapping regression."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aiecs.tools.search_tool.backends.google_cse import GoogleCseBackend
from aiecs.tools.search_tool.backends.protocol import SearchCallParams
from aiecs.tools.search_tool.core import SearchTool


def _cse_config() -> SearchTool.Config:
    return SearchTool.Config.model_construct(
        google_api_key="test-api-key",
        google_cse_id="test-cse-id",
        rate_limit_requests=100,
        rate_limit_window=86400,
        circuit_breaker_threshold=5,
        circuit_breaker_timeout=60,
    )


@pytest.mark.gate_p1
def test_google_cse_applies_date_restrict_and_file_type() -> None:
    mock_service = MagicMock()
    mock_list = MagicMock()
    mock_list.execute.return_value = {"items": []}
    mock_service.cse.return_value.list.return_value = mock_list

    backend = GoogleCseBackend(_cse_config())
    backend.service = mock_service

    params = SearchCallParams(
        query="annual report",
        original_query="annual report",
        num_results=5,
        date_restrict="m3",
        file_type="pdf",
    )
    result = backend.search(params)

    assert result.success is True
    assert "date_restrict" in result.params_applied
    assert "file_type" in result.params_applied

    call_kwargs = mock_service.cse.return_value.list.call_args.kwargs
    assert call_kwargs["dateRestrict"] == "m3"
    assert call_kwargs["fileType"] == "pdf"
    assert call_kwargs["q"] == "annual report"
    assert call_kwargs["cx"] == "test-cse-id"


@pytest.mark.gate_p1
def test_google_cse_exclude_terms_appended_to_query() -> None:
    mock_service = MagicMock()
    mock_list = MagicMock()
    mock_list.execute.return_value = {"items": []}
    mock_service.cse.return_value.list.return_value = mock_list

    backend = GoogleCseBackend(_cse_config())
    backend.service = mock_service

    params = SearchCallParams(
        query="machine learning",
        original_query="machine learning",
        num_results=5,
        exclude_terms=["spam", "ads"],
    )
    result = backend.search(params)

    assert result.success is True
    assert "exclude_terms" in result.params_applied
    call_kwargs = mock_service.cse.return_value.list.call_args.kwargs
    assert call_kwargs["q"] == "machine learning -spam -ads"


@pytest.mark.gate_p1
def test_search_web_cse_path_uses_backend_filters() -> None:
    mock_service = MagicMock()
    mock_list = MagicMock()
    mock_list.execute.return_value = {
        "items": [
            {
                "title": "Report",
                "link": "https://example.com/report.pdf",
                "snippet": "PDF report",
                "displayLink": "example.com",
            }
        ]
    }
    mock_service.cse.return_value.list.return_value = mock_list

    tool = SearchTool(
        config={
            "google_api_key": "test-api-key",
            "google_cse_id": "test-cse-id",
            "enable_intent_analysis": False,
            "enable_context_tracking": False,
            "enable_intelligent_cache": False,
        }
    )
    tool.service = mock_service

    result = tool.search_web(
        query="annual report",
        num_results=5,
        date_restrict="m3",
        file_type="pdf",
        auto_enhance=False,
    )

    assert result["results"]
    call_kwargs = mock_service.cse.return_value.list.call_args.kwargs
    assert call_kwargs["dateRestrict"] == "m3"
    assert call_kwargs["fileType"] == "pdf"
