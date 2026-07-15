"""Tests for OpenAI-compatible reasoning in non-streaming responses."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from openai.types.chat import ChatCompletionMessage

from aiecs.llm.clients.base_client import LLMMessage
from aiecs.llm.clients.openai_compatible_mixin import OpenAICompatibleFunctionCallingMixin
from aiecs.llm.clients.schemas import sanitize_tool_calls


class _NonStreamingTestClient(OpenAICompatibleFunctionCallingMixin):
    provider_name = "test"

    def _sanitize_tool_calls(self, tool_calls):
        return sanitize_tool_calls(tool_calls)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_text_includes_reasoning_content_in_response():
    client = _NonStreamingTestClient()
    message = ChatCompletionMessage.model_validate(
        {
            "role": "assistant",
            "content": "visible answer",
            "reasoning_content": "internal reasoning",
        }
    )
    mock_response = SimpleNamespace(
        choices=[SimpleNamespace(message=message)],
        usage=SimpleNamespace(
            total_tokens=10,
            prompt_tokens=4,
            completion_tokens=6,
            prompt_tokens_details=None,
        ),
    )
    mock_openai = AsyncMock()
    mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)

    response = await client._generate_text_with_function_calling(
        client=mock_openai,
        messages=[LLMMessage(role="user", content="Hello")],
        model="reasoning-model",
        temperature=0.0,
        max_tokens=256,
    )

    assert response.content.startswith("<thinking>\ninternal reasoning\n</thinking>\n")
    assert response.content.endswith("visible answer")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_text_without_reasoning_unchanged():
    client = _NonStreamingTestClient()
    message = ChatCompletionMessage.model_validate(
        {"role": "assistant", "content": "hello"}
    )
    mock_response = SimpleNamespace(
        choices=[SimpleNamespace(message=message)],
        usage=SimpleNamespace(
            total_tokens=5,
            prompt_tokens=2,
            completion_tokens=3,
            prompt_tokens_details=None,
        ),
    )
    mock_openai = AsyncMock()
    mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)

    response = await client._generate_text_with_function_calling(
        client=mock_openai,
        messages=[LLMMessage(role="user", content="Hello")],
        model="plain-model",
        temperature=0.0,
        max_tokens=256,
    )

    assert response.content == "hello"
