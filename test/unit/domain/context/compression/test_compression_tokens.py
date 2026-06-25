"""W8a token estimation tests (OpenHarness golden ±5%)."""

from __future__ import annotations

import pytest

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.constants import (
    AUTOCOMPACT_BUFFER_TOKENS,
    DEFAULT_CONTEXT_WINDOW,
    TOKEN_ESTIMATION_PADDING,
)
from aiecs.domain.context.compression.tokens import (
    estimate_message_tokens,
    estimate_tokens,
    get_autocompact_threshold,
    should_compress_messages,
)


def test_estimate_tokens_openharness_basics() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1


def test_estimate_message_tokens_text_only() -> None:
    messages = [
        LLMMessage(role="user", content="abcd"),
        LLMMessage(role="assistant", content="abcdefgh"),
    ]
    expected_raw = estimate_tokens("abcd") + estimate_tokens("abcdefgh")
    expected = int(expected_raw * TOKEN_ESTIMATION_PADDING)
    assert estimate_message_tokens(messages) == expected


def test_estimate_message_tokens_image_budget(monkeypatch) -> None:
    monkeypatch.setenv("AIECS_IMAGE_TOKEN_ESTIMATE", "6000")
    messages = [
        LLMMessage(
            role="user",
            content=None,
            images=[{"source": "https://example.com/x.png"}],
        )
    ]
    assert estimate_message_tokens(messages) == int(6000 * TOKEN_ESTIMATION_PADDING)


def test_get_autocompact_threshold_default() -> None:
    reserved = min(20_000, 20_000)
    expected = DEFAULT_CONTEXT_WINDOW - reserved - AUTOCOMPACT_BUFFER_TOKENS
    assert get_autocompact_threshold() == expected


def test_should_compress_messages_respects_threshold() -> None:
    short = [LLMMessage(role="user", content="hi")]
    long = [LLMMessage(role="user", content="word " * 50_000)]
    assert should_compress_messages(short, auto_compact_threshold_tokens=1_000_000) is False
    assert should_compress_messages(long, auto_compact_threshold_tokens=10) is True
    assert should_compress_messages(long, enabled=False) is False
    assert should_compress_messages(short, force=True) is True


def test_openharness_golden_within_five_percent() -> None:
    """Spot-check parity with OpenHarness compact block estimator."""
    openharness_estimate = int((1 + 2) * TOKEN_ESTIMATION_PADDING)
    ours = estimate_message_tokens(
        [
            LLMMessage(role="user", content="abcd"),
            LLMMessage(role="assistant", content="abcdefgh"),
        ]
    )
    delta = abs(ours - openharness_estimate) / max(openharness_estimate, 1)
    assert delta <= 0.05
