"""Tests for Gemini thinking chunks in Google streaming function calling.

google-genai Part.thought is a bool flag; summary text lives in part.text.
"""

from types import SimpleNamespace
from typing import Any, AsyncGenerator, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from aiecs.llm.clients.google_function_calling_mixin import GoogleFunctionCallingMixin


class _GoogleStreamingTestClient(GoogleFunctionCallingMixin):
    provider_name = "test"


def _make_stream(chunks: List[Any]) -> AsyncGenerator[Any, None]:
    async def _gen():
        for chunk in chunks:
            yield chunk

    return _gen()


def _google_chunk(
    *,
    thought: Optional[bool] = None,
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
async def test_streaming_forwards_thought_flag_with_text():
    """{thought: True, text: "..."} yields one thought chunk, not a token."""
    client = _GoogleStreamingTestClient()
    stream = _make_stream(
        [
            _google_chunk(thought=True, text="reasoning step"),
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
async def test_streaming_thought_text_not_duplicated_as_token():
    """Thought summary must not also appear as a visible token chunk."""
    client = _GoogleStreamingTestClient()
    stream = _make_stream([_google_chunk(thought=True, text="I should search")])
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
    assert chunks[0].type == "thought"
    assert chunks[0].content == "I should search"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_streaming_skips_flag_only_thought_part():
    """{thought: True} without text yields no thought/token chunks."""
    client = _GoogleStreamingTestClient()
    stream = _make_stream(
        [
            _google_chunk(thought=True, text=None),
            _google_chunk(thought=False, text="answer"),
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

    assert len(chunks) == 1
    assert chunks[0].type == "token"
    assert chunks[0].content == "answer"


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
    """Plain-string streaming mode must not forward thought summary text."""
    client = _GoogleStreamingTestClient()
    stream = _make_stream(
        [
            _google_chunk(thought=True, text="hidden reasoning"),
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


@pytest.mark.asyncio
@pytest.mark.unit
async def test_streaming_usage_forwards_thoughts_token_count():
    """SDK field thoughts_token_count must surface as usage['thinking_tokens']."""
    client = _GoogleStreamingTestClient()

    async def _gen():
        yield SimpleNamespace(
            candidates=[
                SimpleNamespace(
                    content=SimpleNamespace(parts=[SimpleNamespace(thought=None, text="hi")]),
                    finish_reason=None,
                )
            ],
            usage_metadata=SimpleNamespace(
                prompt_token_count=1,
                candidates_token_count=1,
                total_token_count=2,
                cached_content_token_count=None,
                thoughts_token_count=42,
            ),
            prompt_feedback=None,
        )

    mock_client = _mock_google_client(_gen())

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

    usage_chunks = [c for c in chunks if c.type == "usage"]
    assert len(usage_chunks) == 1
    assert usage_chunks[0].usage["thinking_tokens"] == 42
