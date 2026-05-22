"""Regression tests for streaming tool call id handling."""

from types import SimpleNamespace
from typing import Any, AsyncGenerator, Dict, List, Optional
from unittest.mock import AsyncMock

import pytest

from aiecs.llm.clients.openai_compatible_mixin import OpenAICompatibleFunctionCallingMixin, StreamChunk
from aiecs.llm.clients.base_client import LLMMessage
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


def _tool_delta(
    *,
    index: Optional[int] = None,
    call_id: Optional[str] = None,
    name: Optional[str] = None,
    arguments: Optional[str] = None,
) -> SimpleNamespace:
    function = None
    if name is not None or arguments is not None:
        function = SimpleNamespace(name=name, arguments=arguments)
    return SimpleNamespace(index=index, id=call_id, function=function)


def _chunk(*, content: Optional[str] = None, tool_calls: Optional[List[Any]] = None) -> SimpleNamespace:
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)], usage=None)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_streaming_accumulator_uses_index_when_id_missing():
    """Streaming deltas without id must produce stable non-null tool call ids."""
    client = _StreamingTestClient()
    stream = _make_stream(
        [
            _chunk(tool_calls=[_tool_delta(index=0, name="get_weather", arguments="")]),
            _chunk(tool_calls=[_tool_delta(index=0, arguments='{"city": "NYC"}')]),
        ]
    )
    mock_openai = AsyncMock()
    mock_openai.chat.completions.create = AsyncMock(return_value=stream)

    chunks = [
        chunk
        async for chunk in client._stream_text_with_function_calling(
            client=mock_openai,
            messages=[LLMMessage(role="user", content="What's the weather?")],
            model="test-model",
            temperature=0.0,
            max_tokens=256,
            return_chunks=True,
        )
    ]

    tool_calls_chunk = next(c for c in chunks if c.type == "tool_calls")
    assert tool_calls_chunk.tool_calls is not None
    assert len(tool_calls_chunk.tool_calls) == 1
    assert tool_calls_chunk.tool_calls[0]["id"] == "call_0"
    assert tool_calls_chunk.tool_calls[0]["function"]["name"] == "get_weather"
    assert tool_calls_chunk.tool_calls[0]["function"]["arguments"] == '{"city": "NYC"}'


@pytest.mark.asyncio
@pytest.mark.unit
async def test_streaming_accumulator_backfills_provider_id():
    """When id arrives in a later delta, the accumulated call should adopt it."""
    client = _StreamingTestClient()
    stream = _make_stream(
        [
            _chunk(tool_calls=[_tool_delta(index=0, name="search", arguments="")]),
            _chunk(tool_calls=[_tool_delta(index=0, call_id="call_provider_abc", arguments='{"q": "x"}')]),
        ]
    )
    mock_openai = AsyncMock()
    mock_openai.chat.completions.create = AsyncMock(return_value=stream)

    chunks = [
        chunk
        async for chunk in client._stream_text_with_function_calling(
            client=mock_openai,
            messages=[LLMMessage(role="user", content="Search")],
            model="test-model",
            temperature=0.0,
            max_tokens=256,
            return_chunks=True,
        )
    ]

    tool_calls_chunk = next(c for c in chunks if c.type == "tool_calls")
    assert tool_calls_chunk.tool_calls[0]["id"] == "call_provider_abc"


@pytest.mark.unit
def test_sanitize_tool_calls_generates_ids_for_missing_values():
    """Outbound sanitization must never forward id=None to providers."""
    raw = [
        {"id": None, "type": "function", "function": {"name": "foo", "arguments": "{}"}},
        {"type": "function", "function": {"name": "bar", "arguments": "{}"}},
    ]
    sanitized = sanitize_tool_calls(raw)
    assert sanitized is not None
    assert sanitized[0]["id"] == "call_0"
    assert sanitized[1]["id"] == "call_1"


@pytest.mark.unit
def test_convert_messages_preserves_sanitized_tool_call_ids():
    """Follow-up requests must not contain tool_calls[].id=None."""
    client = _StreamingTestClient()
    messages = [
        LLMMessage(
            role="assistant",
            content="Calling tool",
            tool_calls=[{"id": None, "type": "function", "function": {"name": "foo", "arguments": "{}"}}],
        ),
        LLMMessage(role="tool", content="{}", tool_call_id="call_0"),
    ]
    openai_messages = client._convert_messages_to_openai_format(messages)
    assistant = openai_messages[0]
    assert assistant["tool_calls"][0]["id"] == "call_0"
