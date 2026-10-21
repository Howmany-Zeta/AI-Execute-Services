"""prompt_cache_key is set only for an OpenAI request that has a session_id."""

import pytest

from aiecs.llm.clients.base_client import LLMMessage, LLMResponse
from aiecs.llm.clients.openai_client import OpenAIClient


def _response() -> LLMResponse:
    return LLMResponse(content="ok", provider="OpenAI", model="gpt-4o")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_cache_key_requires_session_id_and_retries_once_when_rejected():
    client = OpenAIClient()
    client._get_client = lambda: object()  # type: ignore[method-assign]
    calls: list[dict] = []

    async def _generate(**kwargs):
        calls.append(kwargs)
        if kwargs.get("prompt_cache_key"):
            raise RuntimeError("Unrecognized request argument: prompt_cache_key")
        return _response()

    client._generate_text_with_function_calling = _generate  # type: ignore[method-assign]
    messages = [LLMMessage(role="user", content="hello")]

    await client.generate_text(messages, model="gpt-4o", context={"agent_id": "agent-1"})
    assert "prompt_cache_key" not in calls[-1]

    await client.generate_text(messages, model="gpt-4o", context={"session_id": "sess-1", "agent_id": "agent-1"})
    assert calls[-2]["prompt_cache_key"] == "sess-1"
    assert "prompt_cache_key" not in calls[-1]
    assert len(calls) == 3


@pytest.mark.asyncio
@pytest.mark.unit
async def test_stream_prompt_cache_key_absent_without_session_id():
    client = OpenAIClient()
    client._get_client = lambda: object()  # type: ignore[method-assign]
    calls: list[dict] = []

    async def _stream(**kwargs):
        calls.append(kwargs)
        yield "token"

    client._stream_text_with_function_calling = _stream  # type: ignore[method-assign]
    messages = [LLMMessage(role="user", content="hello")]

    async for _ in client.stream_text(messages, model="gpt-4o", context={}):
        pass
    assert "prompt_cache_key" not in calls[-1]

    async for _ in client.stream_text(messages, model="gpt-4o", context={"session_id": "sess-2"}):
        pass
    assert calls[-1]["prompt_cache_key"] == "sess-2"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_stream_drops_rejected_prompt_cache_key_before_any_token():
    client = OpenAIClient()
    client._get_client = lambda: object()  # type: ignore[method-assign]
    calls: list[dict] = []

    async def _stream(**kwargs):
        calls.append(dict(kwargs))
        if kwargs.get("prompt_cache_key"):
            raise RuntimeError("Unknown parameter: prompt_cache_key")
        yield "token"

    client._stream_text_with_function_calling = _stream  # type: ignore[method-assign]
    messages = [LLMMessage(role="user", content="hello")]

    tokens = []
    async for token in client.stream_text(messages, model="gpt-4o", context={"session_id": "sess-3"}):
        tokens.append(token)

    assert tokens == ["token"]
    assert calls[0]["prompt_cache_key"] == "sess-3"
    assert "prompt_cache_key" not in calls[1]
