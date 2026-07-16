"""P1-01: SearchTool lazy credential init — constructor must not require CSE."""

from __future__ import annotations

import pytest

from aiecs.tools.search_tool.constants import AuthenticationError, ValidationError
from aiecs.tools.search_tool.core import SearchTool


@pytest.mark.gate_p1
def test_search_tool_constructs_without_cse_keys() -> None:
    tool = SearchTool(config={"gemini_api_key": "test-gemini-key"})
    assert tool is not None
    assert hasattr(tool, "_registry")
    assert tool._is_cse_configured() is False


@pytest.mark.gate_p1
def test_search_news_without_cse_keys_raises_at_call_time() -> None:
    tool = SearchTool(config={"gemini_api_key": "test-gemini-key"})
    with pytest.raises((AuthenticationError, ValidationError)):
        tool.search_news("latest technology news")


@pytest.mark.gate_p1
def test_search_images_without_cse_keys_raises_at_call_time() -> None:
    tool = SearchTool(config={"gemini_api_key": "test-gemini-key"})
    with pytest.raises((AuthenticationError, ValidationError)):
        tool.search_images("sunset photos")


@pytest.mark.gate_p1
def test_empty_search_news_query_raises_validation_error_before_cse() -> None:
    tool = SearchTool(config={"google_api_key": "k", "google_cse_id": "cx"})
    with pytest.raises(ValidationError, match="Query cannot be empty"):
        tool.search_news("   ")
