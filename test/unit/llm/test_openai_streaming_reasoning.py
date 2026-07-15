"""Tests for OpenAI-compatible reasoning deltas in streaming function calling."""

from types import SimpleNamespace
from typing import Any, AsyncGenerator, List, Optional
from unittest.mock import AsyncMock

import pytest
from openai.types.chat.chat_completion_chunk import ChoiceDelta

from aiecs.llm.clients.base_client import LLMMessage
from aiecs.llm.clients.openai_compatible_mixin import OpenAICompatibleFunctionCallingMixin
from aiecs.llm.clients.schemas import sanitize_tool_calls


class _StreamingTestClient(OpenAICompatibleFunctionCallingMixin):
    provider_name = "test"

    def _sanitize_tool_calls(self, tool_calls):
        return sanitize_tool_calls(tool_calls)


def _make_stream(chunks: List[Any]) -> AsyncGenerator[Any, None]:
    async def _gen():
        for chunk in chunks:
            yield chunk

    return _gen()


def _chunk(*, delta: Any) -> SimpleNamespace:
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)], usage=None)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_streaming_forwards_reasoning_content_from_model_extra():
    """reasoning_content in delta.model_extra must yield StreamChunk(type='thought')."""
    client = _StreamingTestClient()
    delta = ChoiceDelta.model_validate(
        {"role": "assistant", "content": None, "reasoning_content": "internal step"}
    )
    stream = _make_stream([_chunk(delta=delta)])
    mock_openai = AsyncMock()
    mock_openai.chat.completions.create = AsyncMock(return_value=stream)

    chunks = [
        chunk
        async for chunk in client._stream_text_with_function_calling(
            client=mock_openai,
            messages=[LLMMessage(role="user", content="Think")],
            model="deepseek-reasoner",
            temperature=0.0,
            max_tokens=256,
            return_chunks=True,
        )
    ]

    assert len(chunks) == 1
    assert chunks[0].type == "thought"
    assert chunks[0].content == "internal step"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_streaming_forwards_reasoning_before_visible_content():
    """Reasoning deltas should stream before answer text."""
    client = _StreamingTestClient()
    stream = _make_stream(
        [
            _chunk(
                delta=ChoiceDelta.model_validate(
                    {"role": "assistant", "content": None, "reasoning_content": "thinking"}
                )
            ),
            _chunk(delta=ChoiceDelta.model_validate({"role": "assistant", "content": "hello"})),
        ]
    )
    mock_openai = AsyncMock()
    mock_openai.chat.completions.create = AsyncMock(return_value=stream)

    chunks = [
        chunk
        async for chunk in client._stream_text_with_function_calling(
            client=mock_openai,
            messages=[LLMMessage(role="user", content="Hello")],
            model="reasoning-model",
            temperature=0.0,
            max_tokens=256,
            return_chunks=True,
        )
    ]

    assert [c.type for c in chunks] == ["thought", "token"]
    assert chunks[0].content == "thinking"
    assert chunks[1].content == "hello"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_streaming_supports_reasoning_field_alias():
    """Providers that emit delta.reasoning instead of reasoning_content are supported."""
    client = _StreamingTestClient()
    delta = SimpleNamespace(content=None, tool_calls=None, model_extra={"reasoning": "ollama thought"})
    stream = _make_stream([_chunk(delta=delta)])
    mock_openai = AsyncMock()
    mock_openai.chat.completions.create = AsyncMock(return_value=stream)

    chunks = [
        chunk
        async for chunk in client._stream_text_with_function_calling(
            client=mock_openai,
            messages=[LLMMessage(role="user", content="Hello")],
            model="ollama-reasoning",
            temperature=0.0,
            max_tokens=256,
            return_chunks=True,
        )
    ]

    assert len(chunks) == 1
    assert chunks[0].type == "thought"
    assert chunks[0].content == "ollama thought"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_streaming_drops_reasoning_when_return_chunks_false():
    """Plain-string streaming mode must not forward internal reasoning content."""
    client = _StreamingTestClient()
    stream = _make_stream(
        [
            _chunk(
                delta=ChoiceDelta.model_validate(
                    {"role": "assistant", "content": None, "reasoning_content": "hidden"}
                )
            ),
            _chunk(delta=ChoiceDelta.model_validate({"role": "assistant", "content": "visible"})),
        ]
    )
    mock_openai = AsyncMock()
    mock_openai.chat.completions.create = AsyncMock(return_value=stream)

    chunks = [
        chunk
        async for chunk in client._stream_text_with_function_calling(
            client=mock_openai,
            messages=[LLMMessage(role="user", content="Hello")],
            model="reasoning-model",
            temperature=0.0,
            max_tokens=256,
            return_chunks=False,
        )
    ]

    assert chunks == ["visible"]
