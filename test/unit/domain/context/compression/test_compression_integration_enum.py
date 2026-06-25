"""integration.ContextCompressor strategy coverage."""

from __future__ import annotations

from dataclasses import dataclass

from aiecs.llm import LLMMessage

from aiecs.domain.agent.integration.context_compressor import (
    CompressionStrategy,
    ContextCompressor,
)


@dataclass
class _MockResponse:
    content: str


class _MockLLMClient:
    async def generate_text(self, *, messages, max_tokens, system_prompt=""):
        _ = messages, max_tokens, system_prompt
        return _MockResponse(content="<summary>integration summary</summary>")


def _sample_messages(count: int = 10) -> list[LLMMessage]:
    return [
        LLMMessage(
            role="user" if index % 2 == 0 else "assistant",
            content=f"message-{index}-" + ("x" * 200),
        )
        for index in range(count)
    ]


def test_preserve_recent_strategy() -> None:
    messages = _sample_messages()
    compressor = ContextCompressor(
        max_tokens=100,
        strategy=CompressionStrategy.PRESERVE_RECENT,
    )
    compressed = compressor.compress_messages(messages)
    assert len(compressed) <= len(messages)


def test_truncate_middle_strategy() -> None:
    messages = [
        LLMMessage(
            role="user" if index % 2 == 0 else "assistant",
            content=f"message-{index}-" + ("x" * 40),
        )
        for index in range(6)
    ]
    compressor = ContextCompressor(
        max_tokens=30,
        strategy=CompressionStrategy.TRUNCATE_MIDDLE,
    )
    compressed = compressor.compress_messages(messages)
    assert len(compressed) < len(messages)
    assert any(
        "compressed" in (message.content or "")
        or "earlier messages omitted" in (message.content or "")
        for message in compressed
    )


def test_truncate_start_strategy() -> None:
    messages = _sample_messages()
    compressor = ContextCompressor(
        max_tokens=100,
        strategy=CompressionStrategy.TRUNCATE_START,
    )
    compressed = compressor.compress_messages(messages)
    assert compressed
    assert compressed[-1].content == messages[-1].content


def test_summarize_without_llm_uses_legacy_compact() -> None:
    messages = _sample_messages()
    compressor = ContextCompressor(
        max_tokens=100,
        strategy=CompressionStrategy.SUMMARIZE,
    )
    compressed = compressor.compress_messages(messages)
    assert len(compressed) < len(messages)
    assert "[conversation summary]" in (compressed[0].content or "")


def test_summarize_with_llm_delegates_to_kernel() -> None:
    messages = _sample_messages()
    compressor = ContextCompressor(
        max_tokens=100,
        strategy=CompressionStrategy.SUMMARIZE,
        llm_client=_MockLLMClient(),
    )
    compressed = compressor.compress_messages(messages)
    assert len(compressed) < len(messages)
    assert any(
        "continued from a previous conversation" in (message.content or "")
        or "Compact boundary marker" in (message.content or "")
        for message in compressed
    )


def test_estimate_tokens_delegates_to_kernel() -> None:
    import inspect

    from aiecs.domain.agent.integration import context_compressor as module

    source = inspect.getsource(module.ContextCompressor._estimate_tokens)
    assert "len(msg.content or \"\") // 4" not in source
    assert "estimate_message_tokens" in source
