"""Tests for Gemini thought_signature round-trip on function calls and content parts."""

from __future__ import annotations

import base64
from types import SimpleNamespace
from typing import Any, AsyncGenerator, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from google.genai import types

from aiecs.llm.clients.base_client import LLMMessage
from aiecs.llm.clients.google_function_calling_mixin import (
    SKIP_THOUGHT_SIGNATURE_VALIDATOR,
    GoogleFunctionCallingMixin,
    build_content_and_signature_from_google_parts,
    build_google_function_call_part,
    deserialize_thought_signature,
    serialize_thought_signature,
)
from aiecs.llm.clients.schemas import sanitize_tool_calls


class _GoogleSignatureTestClient(GoogleFunctionCallingMixin):
    provider_name = "test"

    def _sanitize_tool_calls(self, tool_calls):
        return sanitize_tool_calls(tool_calls)


def _part(
    *,
    thought: Optional[bool] = None,
    text: Optional[str] = None,
    function_call: Any = None,
    thought_signature: Any = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        thought=thought,
        text=text,
        function_call=function_call,
        thought_signature=thought_signature,
    )


def _make_stream(chunks: List[Any]) -> AsyncGenerator[Any, None]:
    async def _gen():
        for chunk in chunks:
            yield chunk

    return _gen()


def _mock_google_client(stream: AsyncGenerator[Any, None]) -> MagicMock:
    client = MagicMock()

    async def _generate_content_stream(*_args, **_kwargs):
        return stream

    client.aio.models.generate_content_stream = AsyncMock(side_effect=_generate_content_stream)
    return client


@pytest.mark.unit
def test_serialize_deserialize_thought_signature_roundtrip():
    raw = b"opaque-signature-bytes"
    stored = serialize_thought_signature(raw)
    assert stored == base64.b64encode(raw).decode("ascii")
    assert deserialize_thought_signature(stored) == raw


@pytest.mark.unit
def test_serialize_skip_sentinel():
    assert serialize_thought_signature(SKIP_THOUGHT_SIGNATURE_VALIDATOR.encode("utf-8")) == SKIP_THOUGHT_SIGNATURE_VALIDATOR
    assert deserialize_thought_signature(SKIP_THOUGHT_SIGNATURE_VALIDATOR) == SKIP_THOUGHT_SIGNATURE_VALIDATOR.encode(
        "utf-8"
    )


@pytest.mark.unit
def test_build_function_call_part_uses_stored_signature():
    sig = base64.b64encode(b"sig-abc").decode("ascii")
    part = build_google_function_call_part("web_search", {"q": "x"}, thought_signature=sig)
    assert part.function_call is not None
    assert part.function_call.name == "web_search"
    assert part.thought_signature == b"sig-abc"


@pytest.mark.unit
def test_build_function_call_part_fallback_skip_when_required():
    part = build_google_function_call_part("web_search", {}, thought_signature=None, require_signature=True)
    assert part.thought_signature == SKIP_THOUGHT_SIGNATURE_VALIDATOR.encode("utf-8")


@pytest.mark.unit
def test_build_function_call_part_omits_signature_when_not_required():
    part = build_google_function_call_part("web_search", {}, thought_signature=None, require_signature=False)
    assert part.thought_signature is None


@pytest.mark.unit
def test_sanitize_tool_calls_preserves_thought_signature():
    sig = base64.b64encode(b"keep-me").decode("ascii")
    sanitized = sanitize_tool_calls(
        [
            {
                "id": "call_0",
                "type": "function",
                "function": {"name": "web_search", "arguments": '{"q": "x"}'},
                "thought_signature": sig,
            }
        ]
    )
    assert sanitized is not None
    assert sanitized[0]["thought_signature"] == sig


@pytest.mark.unit
def test_extract_function_calls_captures_part_thought_signature():
    client = _GoogleSignatureTestClient()
    sig = b"fc-signature"
    response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[
                        _part(
                            function_call=SimpleNamespace(id="call_1", name="web_search", args={"q": "gemini"}),
                            thought_signature=sig,
                        )
                    ]
                )
            )
        ]
    )
    calls = client._extract_function_calls_from_google_response(response)
    assert calls is not None
    assert calls[0]["function"]["name"] == "web_search"
    assert calls[0]["thought_signature"] == base64.b64encode(sig).decode("ascii")


@pytest.mark.unit
def test_build_content_captures_thought_part_signature():
    sig = b"thought-sig"
    content, content_sig = build_content_and_signature_from_google_parts(
        [
            _part(thought=True, text="reasoning", thought_signature=sig),
            _part(text="answer"),
        ]
    )
    assert "<thinking>" in content
    assert content.endswith("answer")
    assert content_sig == base64.b64encode(sig).decode("ascii")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_streaming_captures_function_call_thought_signature():
    client = _GoogleSignatureTestClient()
    sig = b"stream-fc-sig"
    chunk = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[
                        _part(
                            function_call=SimpleNamespace(id="call_0", name="web_search", args={"q": "x"}),
                            thought_signature=sig,
                        )
                    ]
                ),
                finish_reason=None,
            )
        ],
        usage_metadata=None,
        prompt_feedback=None,
    )
    mock_client = _mock_google_client(_make_stream([chunk]))

    chunks = [
        c
        async for c in client._stream_text_with_function_calling(
            client=mock_client,
            model_name="gemini-3.5-flash",
            contents="prompt",
            config=SimpleNamespace(),
            return_chunks=True,
        )
    ]

    tool_calls_chunk = next(c for c in chunks if c.type == "tool_calls")
    assert tool_calls_chunk.tool_calls is not None
    assert tool_calls_chunk.tool_calls[0]["thought_signature"] == base64.b64encode(sig).decode("ascii")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_streaming_forwards_thought_part_signature():
    client = _GoogleSignatureTestClient()
    sig = b"stream-thought-sig"
    chunk = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[_part(thought=True, text="reasoning step", thought_signature=sig)]
                ),
                finish_reason=None,
            )
        ],
        usage_metadata=None,
        prompt_feedback=None,
    )
    mock_client = _mock_google_client(_make_stream([chunk]))

    chunks = [
        c
        async for c in client._stream_text_with_function_calling(
            client=mock_client,
            model_name="gemini-3.5-flash",
            contents="prompt",
            config=SimpleNamespace(),
            return_chunks=True,
        )
    ]

    assert len(chunks) == 1
    assert chunks[0].type == "thought"
    assert chunks[0].thought_signature == base64.b64encode(sig).decode("ascii")


@pytest.mark.unit
def test_vertex_convert_replays_function_call_thought_signature():
    from aiecs.llm.clients.vertex_client import VertexAIClient

    client = VertexAIClient.__new__(VertexAIClient)
    sig = base64.b64encode(b"replay-me").decode("ascii")
    messages = [
        LLMMessage(role="user", content="search something"),
        LLMMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": "call_0",
                    "type": "function",
                    "function": {"name": "web_search", "arguments": '{"q": "x"}'},
                    "thought_signature": sig,
                }
            ],
            thought_signature=base64.b64encode(b"content-sig").decode("ascii"),
        ),
        LLMMessage(role="tool", content='{"result": "ok"}', tool_call_id="call_0"),
    ]

    contents = client._convert_messages_to_contents(messages)
    model_content = next(c for c in contents if c.role == "model")
    fc_parts = [p for p in model_content.parts if p.function_call is not None]
    assert len(fc_parts) == 1
    assert fc_parts[0].thought_signature == b"replay-me"
    assert isinstance(fc_parts[0], types.Part)


@pytest.mark.unit
def test_vertex_convert_skip_fallback_for_missing_first_signature():
    from aiecs.llm.clients.vertex_client import VertexAIClient

    client = VertexAIClient.__new__(VertexAIClient)
    messages = [
        LLMMessage(role="user", content="search"),
        LLMMessage(
            role="assistant",
            tool_calls=[
                {
                    "id": "call_0",
                    "type": "function",
                    "function": {"name": "web_search", "arguments": "{}"},
                }
            ],
        ),
    ]

    contents = client._convert_messages_to_contents(messages)
    model_content = next(c for c in contents if c.role == "model")
    fc_part = next(p for p in model_content.parts if p.function_call is not None)
    assert fc_part.thought_signature == SKIP_THOUGHT_SIGNATURE_VALIDATOR.encode("utf-8")
