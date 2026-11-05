"""Gemini structured output forwards response_schema, not only the JSON mime type."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from aiecs.llm.clients.base_client import LLMMessage
from aiecs.llm.clients.googleai_client import GoogleAIClient
from aiecs.llm.clients.vertex_client import VertexAIClient


class EdgeDuplicate(BaseModel):
    duplicate_facts: list[int]
    contradicted_facts: list[int]


def _response() -> SimpleNamespace:
    return SimpleNamespace(
        text='{"duplicate_facts": [], "contradicted_facts": []}',
        candidates=None,
        prompt_feedback=None,
        usage_metadata=SimpleNamespace(
            prompt_token_count=4,
            candidates_token_count=2,
            total_token_count=6,
            cached_content_token_count=None,
        ),
    )


def _assert_schema(config: object) -> None:
    assert getattr(config, "response_mime_type") == "application/json"
    assert getattr(config, "response_schema") is EdgeDuplicate


@pytest.mark.asyncio
@pytest.mark.unit
async def test_vertex_generate_text_forwards_response_schema() -> None:
    client = VertexAIClient()
    api = AsyncMock()
    api.aio.models.generate_content = AsyncMock(return_value=_response())
    client._init_client = lambda: api  # type: ignore[method-assign]

    await client.generate_text(
        [LLMMessage(role="user", content="dedupe")],
        model="gemini-2.5-flash",
        response_schema=EdgeDuplicate,
        input_price=0.0,
        output_price=0.0,
    )

    _assert_schema(api.aio.models.generate_content.await_args.kwargs["config"])


@pytest.mark.asyncio
@pytest.mark.unit
async def test_googleai_generate_text_forwards_response_schema() -> None:
    client = GoogleAIClient()
    api = AsyncMock()
    api.aio.models.generate_content = AsyncMock(return_value=_response())
    client._init_google_ai = lambda: api  # type: ignore[method-assign]

    await client.generate_text(
        [LLMMessage(role="user", content="dedupe")],
        model="gemini-2.5-flash",
        response_schema=EdgeDuplicate,
        input_price=0.0,
        output_price=0.0,
    )

    _assert_schema(api.aio.models.generate_content.await_args.kwargs["config"])
