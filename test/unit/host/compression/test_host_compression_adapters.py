"""Unit tests for M4 host compression adapters (CC-092–095)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.context.compression.policy import CompressionPolicy
from aiecs.domain.context.compression.progress import CompactProgressEvent
from aiecs.host.compression.config import use_aiecs_compression
from aiecs.host.compression.l2_mc_adapter import compact_at_mc_recursive_boundary
from aiecs.host.compression.progress_bridge import compact_progress_event_to_sse_payload
from aiecs.host.compression.s3_tool_artifact_port import S3ToolArtifactPort
from aiecs.host.compression.transcript_compact import compact_formatted_transcript
from aiecs.llm import LLMMessage


def test_use_aiecs_compression_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("USE_AIECS_COMPRESSION", raising=False)
    assert use_aiecs_compression() is False
    monkeypatch.setenv("USE_AIECS_COMPRESSION", "1")
    assert use_aiecs_compression() is True


def test_compact_progress_event_to_sse_payload() -> None:
    event = CompactProgressEvent(
        phase="microcompact_done",
        pre_tokens=1000,
        post_tokens=400,
        checkpoint="microcompact",
    )
    payload = compact_progress_event_to_sse_payload(
        event,
        session_id="s1",
        task_id="t1",
    )
    assert payload["event"] == "context_compact_progress"
    assert payload["phase"] == "microcompact_done"
    assert payload["session_id"] == "s1"
    assert payload["pre_tokens"] == 1000


def test_compact_progress_retry_phases_set_retry_flag() -> None:
    from aiecs.host.compression.progress_bridge import (
        RETRY_COMPACT_PROGRESS_PHASES,
        is_known_compact_progress_phase,
    )

    assert "compact_retry" in RETRY_COMPACT_PROGRESS_PHASES
    event = CompactProgressEvent(phase="compact_retry_prompt_too_long")
    payload = compact_progress_event_to_sse_payload(event)
    assert payload["retry"] is True
    assert is_known_compact_progress_phase("compact_retry")


def test_estimate_transcript_tokens_host_reexport() -> None:
    from aiecs.host.compression import estimate_transcript_tokens

    assert estimate_transcript_tokens([{"role": "user", "content": "hello"}]) > 0


@pytest.mark.asyncio
async def test_f1_summary_chunk_size_propagates_to_chunked_summarize() -> None:
    """G7: L2 F1 passes summary_chunk_size through to chunked LLM summarize."""
    from dataclasses import dataclass

    @dataclass
    class _MockResponse:
        content: str

    class _MockLLMClient:
        def __init__(self) -> None:
            self.calls: list[list] = []

        async def generate_text(self, *, messages, max_tokens, system_prompt=""):
            self.calls.append(list(messages))
            return _MockResponse(content="<summary>chunk summary</summary>")

    transcript = [
        {"role": "user" if index % 2 == 0 else "assistant", "content": "word " * 300}
        for index in range(12)
    ]
    transcript.extend(
        [
            {"role": "user", "content": "recent question"},
            {"role": "assistant", "content": "recent answer"},
        ]
    )
    client = _MockLLMClient()
    policy = CompressionPolicy(
        enabled=True,
        preserve_recent=2,
        summary_chunk_size=500,
        auto_compact_threshold_tokens=1,
    )

    rows, did_compact = await compact_formatted_transcript(
        transcript,
        policy=policy,
        llm_client=client,
        force=True,
    )

    assert did_compact is True
    assert len(client.calls) >= 2
    assert len(rows) < len(transcript)
    assert any("continued from a previous conversation" in (row.get("content") or "") for row in rows)


@pytest.mark.asyncio
async def test_l2_adapter_summarize_redirects_to_f1_without_microcompact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """G3: legacy summarize on text dump must not invoke microcompact_messages."""
    monkeypatch.setenv("USE_AIECS_COMPRESSION", "true")
    history = [{"role": "user", "content": "x" * 5000}]

    with patch(
        "aiecs.host.compression.l2_mc_adapter.compact_formatted_transcript",
        new=AsyncMock(return_value=([{"role": "user", "content": "summary"}], True)),
    ) as mock_f1:
        with patch(
            "aiecs.domain.context.compression.microcompact.microcompact_messages",
        ) as mock_micro:
            result, did = await compact_at_mc_recursive_boundary(
                history,
                policy=CompressionPolicy(enabled=True),
                llm_client=AsyncMock(),
                strategy="summarize",
            )

    assert did is True
    assert result[0].content == "summary"
    mock_f1.assert_awaited_once()
    mock_micro.assert_not_called()


@pytest.mark.asyncio
async def test_l2_adapter_tuple_strategy_on_text_dump_redirects_to_f1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """G3: explicit tuple strategy on text dump must still use F1, not microcompact."""
    monkeypatch.setenv("USE_AIECS_COMPRESSION", "true")
    history = [{"role": "user", "content": "x" * 5000}]

    with patch(
        "aiecs.host.compression.l2_mc_adapter.compact_formatted_transcript",
        new=AsyncMock(return_value=([{"role": "user", "content": "summary"}], True)),
    ) as mock_f1:
        with patch(
            "aiecs.host.compression.l2_mc_adapter.auto_compact_if_needed",
            new=AsyncMock(),
        ) as mock_compact:
            result, did = await compact_at_mc_recursive_boundary(
                history,
                policy=CompressionPolicy(enabled=True),
                llm_client=AsyncMock(),
                strategy=("microcompact",),
            )

    assert did is True
    assert result[0].content == "summary"
    mock_f1.assert_awaited_once()
    mock_compact.assert_not_awaited()


@pytest.mark.asyncio
async def test_l2_adapter_calls_orchestrator_for_structured_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("USE_AIECS_COMPRESSION", "true")
    compacted = [LLMMessage(role="tool", content="compact", tool_call_id="call_1")]
    history = [
        LLMMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "search", "arguments": "{}"},
                }
            ],
        ),
        LLMMessage(role="tool", content="x" * 5000, tool_call_id="call_1"),
    ]

    with patch(
        "aiecs.host.compression.l2_mc_adapter.auto_compact_if_needed",
        new=AsyncMock(return_value=(compacted, True)),
    ) as mock_compact:
        with patch(
            "aiecs.host.compression.l2_mc_adapter.compact_formatted_transcript",
            new=AsyncMock(),
        ) as mock_f1:
            result, did = await compact_at_mc_recursive_boundary(
                history,
                policy=CompressionPolicy(enabled=True, auto_compact_threshold_tokens=100),
                llm_client=AsyncMock(),
                session_id="sess",
                strategy=("microcompact",),
            )

    assert did is True
    assert result == compacted
    mock_compact.assert_awaited_once()
    mock_f1.assert_not_awaited()


@pytest.mark.asyncio
async def test_l2_adapter_forwards_compression_ports_to_f1_for_text_dump(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aiecs.domain.context.compression.hooks import HookExecutor, HookRegistry
    from aiecs.domain.context.compression.types import InMemorySessionMemoryPort

    monkeypatch.setenv("USE_AIECS_COMPRESSION", "true")
    session_memory = InMemorySessionMemoryPort()
    hooks = HookExecutor(HookRegistry())
    progress = MagicMock()

    with patch(
        "aiecs.host.compression.l2_mc_adapter.compact_formatted_transcript",
        new=AsyncMock(return_value=([{"role": "user", "content": "compact"}], True)),
    ) as mock_f1:
        result, did = await compact_at_mc_recursive_boundary(
            [{"role": "user", "content": "x" * 5000}],
            policy=CompressionPolicy(enabled=True, auto_compact_threshold_tokens=100),
            llm_client=AsyncMock(),
            session_id="sess-l2",
            strategy=("microcompact",),
            session_memory=session_memory,
            hooks=hooks,
            progress=progress,
        )

    assert did is True
    assert result[0].content == "compact"
    mock_f1.assert_awaited_once()
    assert mock_f1.await_args.kwargs["session_id"] == "sess-l2"
    assert mock_f1.await_args.kwargs["session_memory"] is session_memory
    assert mock_f1.await_args.kwargs["hooks"] is hooks
    assert mock_f1.await_args.kwargs["progress"] is progress


@pytest.mark.asyncio
async def test_l2_adapter_noop_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("USE_AIECS_COMPRESSION", raising=False)
    history = [{"role": "user", "content": "hello"}]
    result, did = await compact_at_mc_recursive_boundary(
        history,
        policy=CompressionPolicy(enabled=True),
        llm_client=AsyncMock(),
    )
    assert did is False
    assert len(result) == 1
    assert result[0].content == "hello"


@pytest.mark.asyncio
async def test_s3_tool_artifact_port_stores_and_returns_uri(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AIECS_TOOL_ARTIFACT_BUCKET", "test-bucket")
    mock_client = MagicMock()
    port = S3ToolArtifactPort(client=mock_client, endpoint_url="http://minio:9000")

    uri = await port.store_tool_output(
        session_id="sess/a",
        tool_call_id="call-1",
        content="large payload",
    )

    mock_client.put_object.assert_called_once()
    assert "test-bucket" in mock_client.put_object.call_args.kwargs["Bucket"]
    assert "http://minio:9000/test-bucket/" in uri
