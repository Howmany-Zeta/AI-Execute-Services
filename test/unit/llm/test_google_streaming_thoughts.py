"""Tests for Gemini thinking chunks in Google streaming function calling."""

from types import SimpleNamespace
from typing import Any, AsyncGenerator, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from aiecs.llm.clients.google_function_calling_mixin import GoogleFunctionCallingMixin
from aiecs.llm.clients.openai_compatible_mixin import StreamChunk


class _GoogleStreamingTestClient(GoogleFunctionCallingMixin):
    provider_name = "test"


def _make_stream(chunks: List[Any]) -> AsyncGenerator[Any, None]:
    async def _gen():
        for chunk in chunks:
            yield chunk

    return _gen()


def _google_chunk(
    *,
    thought: Optional[str] = None,
    text: Optional[str] = None,
) -> SimpleNamespace:
    part = SimpleNamespace(thought=thought, text=text)
    content = SimpleNamespace(parts=[part])
    candidate = SimpleNamespace(content=content, finish_reason=None)
    return SimpleNamespace(candidates=[candidate], usage_metadata=None, prompt_feedback=None)


def _mock_google_client(stream: AsyncGenerator[Any, None]) -> MagicMock:
    client = MagicMock()

    async def _generate_content_stream(*_args, **_kwargs):
        return stream

    client.aio.models.generate_content_stream = AsyncMock(side_effect=_generate_content_stream)
    return client


@pytest.mark.asyncio
@pytest.mark.unit
async def test_streaming_forwards_thought_chunks():
    """part.thought must yield StreamChunk(type='thought') before visible text."""
    client = _GoogleStreamingTestClient()
    stream = _make_stream(
        [
            _google_chunk(thought="reasoning step", text=None),
            _google_chunk(thought=None, text="hello"),
        ]
    )
    mock_client = _mock_google_client(stream)

    chunks = [
        chunk
        async for chunk in client._stream_text_with_function_calling(
            client=mock_client,
            model_name="gemini-2.5-flash",
            contents="prompt",
            config=SimpleNamespace(),
            return_chunks=True,
        )
    ]

    assert [c.type for c in chunks] == ["thought", "token"]
    assert chunks[0].content == "reasoning step"
    assert chunks[1].content == "hello"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_streaming_text_only_unchanged():
    """Streams without part.thought must behave as before."""
    client = _GoogleStreamingTestClient()
    stream = _make_stream([_google_chunk(text="hello")])
    mock_client = _mock_google_client(stream)

    chunks = [
        chunk
        async for chunk in client._stream_text_with_function_calling(
            client=mock_client,
            model_name="gemini-2.5-flash",
            contents="prompt",
            config=SimpleNamespace(),
            return_chunks=True,
        )
    ]

    assert len(chunks) == 1
    assert chunks[0].type == "token"
    assert chunks[0].content == "hello"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_streaming_drops_thought_when_return_chunks_false():
    """Plain-string streaming mode must not forward internal thought content."""
    client = _GoogleStreamingTestClient()
    stream = _make_stream(
        [
            _google_chunk(thought="hidden reasoning", text=None),
            _google_chunk(thought=None, text="visible"),
        ]
    )
    mock_client = _mock_google_client(stream)

    chunks = [
        chunk
        async for chunk in client._stream_text_with_function_calling(
            client=mock_client,
            model_name="gemini-2.5-flash",
            contents="prompt",
            config=SimpleNamespace(),
            return_chunks=False,
        )
    ]

    assert chunks == ["visible"]
