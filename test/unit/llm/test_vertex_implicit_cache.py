"""Vertex requests stay on implicit caching and never call caches.create."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from aiecs.llm.clients.base_client import CacheControl, LLMMessage
from aiecs.llm.clients.vertex_client import VertexAIClient


def _response() -> SimpleNamespace:
    part = SimpleNamespace(text="ok", thought=False, function_call=None, thought_signature=None)
    candidate = SimpleNamespace(content=SimpleNamespace(parts=[part]), finish_reason="STOP")
    return SimpleNamespace(
        text="ok",
        candidates=[candidate],
        prompt_feedback=None,
        usage_metadata=SimpleNamespace(
            prompt_token_count=8,
            candidates_token_count=1,
            total_token_count=9,
            cached_content_token_count=4,
        ),
    )


def _messages() -> list:
    return [
        LLMMessage(role="system", content="stable system", cache_control=CacheControl(type="ephemeral")),
        LLMMessage(role="user", content="hello"),
    ]


def _tools() -> list:
    return [
        {
            "type": "function",
            "function": {
                "name": "echo",
                "description": "echo",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]


def _client() -> tuple[VertexAIClient, AsyncMock]:
    client = VertexAIClient()
    api = AsyncMock()
    api.aio.caches.create = AsyncMock()
    api.aio.models.generate_content = AsyncMock(return_value=_response())
    client._init_client = lambda: api  # type: ignore[method-assign]
    return client, api


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_text_sends_system_and_tools_without_cached_content():
    client, api = _client()

    response = await client.generate_text(
        _messages(),
        model="gemini-2.5-pro",
        tools=_tools(),
        input_price=0.0,
        output_price=0.0,
    )

    api.aio.caches.create.assert_not_called()
    config = api.aio.models.generate_content.await_args.kwargs["config"]
    assert config.system_instruction == "stable system"
    assert config.tools
    assert not getattr(config, "cached_content", None)
    assert response.cache_read_tokens == 4
    assert response.cache_hit is True


@pytest.mark.asyncio
@pytest.mark.unit
async def test_stream_text_sends_system_and_tools_without_cached_content():
    client, api = _client()
    captured: dict = {}

    async def _stream(**kwargs):
        captured["config"] = kwargs["config"]
        captured["contents"] = kwargs["contents"]
        if False:
            yield None

    client._stream_text_with_function_calling = _stream  # type: ignore[method-assign]

    chunks = []
    async for chunk in client.stream_text(
        _messages(),
        model="gemini-2.5-pro",
        tools=_tools(),
        return_chunks=True,
    ):
        chunks.append(chunk)

    api.aio.caches.create.assert_not_called()
    assert chunks == []
    assert captured["config"].system_instruction == "stable system"
    assert captured["config"].tools
    assert not getattr(captured["config"], "cached_content", None)
    assert captured["contents"] == "hello"
