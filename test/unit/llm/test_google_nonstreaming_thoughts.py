"""Tests for Gemini thought handling in non-streaming responses.

google-genai Part.thought is a bool flag; summary text lives in part.text.
"""

from types import SimpleNamespace

import pytest

from aiecs.llm.clients.google_function_calling_mixin import (
    build_content_from_google_parts,
    extract_content_from_google_response,
)


def _part(*, thought=None, text=None) -> SimpleNamespace:
    return SimpleNamespace(thought=thought, text=text)


@pytest.mark.unit
def test_build_content_wraps_thought_flag_text():
    content = build_content_from_google_parts(
        [
            _part(thought=True, text="internal reasoning"),
            _part(thought=None, text="visible answer"),
        ]
    )

    assert content.startswith("<thinking>\ninternal reasoning\n</thinking>\n")
    assert content.endswith("visible answer")
    assert "True" not in content


@pytest.mark.unit
def test_build_content_does_not_duplicate_thought_text():
    content = build_content_from_google_parts([_part(thought=True, text="summary only")])

    assert content == "<thinking>\nsummary only\n</thinking>\n"


@pytest.mark.unit
def test_build_content_skips_flag_only_thought():
    content = build_content_from_google_parts(
        [
            _part(thought=True, text=None),
            _part(text="hello"),
        ]
    )

    assert content == "hello"


@pytest.mark.unit
def test_build_content_from_google_parts_text_only_unchanged():
    content = build_content_from_google_parts([_part(text="hello")])

    assert content == "hello"


@pytest.mark.unit
def test_extract_content_from_google_response_prefers_parts_over_text():
    response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[
                        _part(thought=True, text="reasoning"),
                        _part(text="answer"),
                    ]
                )
            )
        ],
        text="text-only fallback",
    )

    content = extract_content_from_google_response(response)

    assert "<thinking>" in content
    assert "reasoning" in content
    assert content.endswith("answer")
    assert "text-only fallback" not in content
    assert "True" not in content


@pytest.mark.unit
def test_extract_content_from_google_response_falls_back_to_text():
    response = SimpleNamespace(
        candidates=[],
        text="plain response",
    )

    assert extract_content_from_google_response(response) == "plain response"
