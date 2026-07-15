"""Tests for Gemini thought handling in non-streaming responses."""

from types import SimpleNamespace

import pytest

from aiecs.llm.clients.google_function_calling_mixin import (
    build_content_from_google_parts,
    extract_content_from_google_response,
)


def _part(*, thought=None, text=None) -> SimpleNamespace:
    return SimpleNamespace(thought=thought, text=text)


def _response(*, parts=None, text=None, text_raises: bool = False) -> SimpleNamespace:
    candidate = None
    if parts is not None:
        candidate = SimpleNamespace(content=SimpleNamespace(parts=parts))

    response = SimpleNamespace(candidates=[candidate] if candidate else [])

    if text_raises:

        def _raise_text():
            raise ValueError("multiple parts")

        response.text = property(lambda self: (_raise_text() or ""))  # type: ignore[method-assign]
    elif text is not None:
        response.text = text

    return response


@pytest.mark.unit
def test_build_content_from_google_parts_includes_thought_before_text():
    content = build_content_from_google_parts(
        [
            _part(thought="internal reasoning"),
            _part(text="visible answer"),
        ]
    )

    assert content.startswith("<thinking>\ninternal reasoning\n</thinking>\n")
    assert content.endswith("visible answer")


@pytest.mark.unit
def test_build_content_from_google_parts_text_only_unchanged():
    content = build_content_from_google_parts([_part(text="hello")])

    assert content == "hello"


@pytest.mark.unit
def test_extract_content_from_google_response_prefers_parts_over_text():
    response = _response(
        parts=[_part(thought="reasoning"), _part(text="answer")],
        text="text-only fallback",
    )

    content = extract_content_from_google_response(response)

    assert "<thinking>" in content
    assert "reasoning" in content
    assert content.endswith("answer")
    assert "text-only fallback" not in content


@pytest.mark.unit
def test_extract_content_from_google_response_falls_back_to_text():
    response = SimpleNamespace(
        candidates=[],
        text="plain response",
    )

    assert extract_content_from_google_response(response) == "plain response"
