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
async def test_l2_adapter_calls_orchestrator_when_flag_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("USE_AIECS_COMPRESSION", "true")
    compacted = [LLMMessage(role="user", content="compact")]

    with patch(
        "aiecs.host.compression.l2_mc_adapter.auto_compact_if_needed",
        new=AsyncMock(return_value=(compacted, True)),
    ) as mock_compact:
        result, did = await compact_at_mc_recursive_boundary(
            [{"role": "user", "content": "x" * 5000}],
            policy=CompressionPolicy(enabled=True, auto_compact_threshold_tokens=100),
            llm_client=AsyncMock(),
            session_id="sess",
            strategy=("microcompact",),
        )

    assert did is True
    assert result == compacted
    mock_compact.assert_awaited_once()


@pytest.mark.asyncio
async def test_l2_adapter_forwards_compression_ports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aiecs.domain.context.compression.hooks import HookExecutor, HookRegistry
    from aiecs.domain.context.compression.tool_budget import InMemoryToolBudgetStore
    from aiecs.domain.context.compression.types import InMemorySessionMemoryPort

    monkeypatch.setenv("USE_AIECS_COMPRESSION", "true")
    compacted = [LLMMessage(role="user", content="compact")]
    session_memory = InMemorySessionMemoryPort()
    hooks = HookExecutor(HookRegistry())
    progress = MagicMock()
    artifact_port = MagicMock()
    budget_store = InMemoryToolBudgetStore()

    with patch(
        "aiecs.host.compression.l2_mc_adapter.enforce_tool_result_budget",
        new=AsyncMock(return_value=[LLMMessage(role="user", content="budgeted")]),
    ) as mock_a8:
        with patch(
            "aiecs.host.compression.l2_mc_adapter.auto_compact_if_needed",
            new=AsyncMock(return_value=(compacted, True)),
        ) as mock_compact:
            result, did = await compact_at_mc_recursive_boundary(
                [{"role": "user", "content": "x" * 5000}],
                policy=CompressionPolicy(enabled=True, auto_compact_threshold_tokens=100),
                llm_client=AsyncMock(),
                session_id="sess-l2",
                strategy=("microcompact",),
                session_memory=session_memory,
                hooks=hooks,
                progress=progress,
                artifact_port=artifact_port,
                budget_store=budget_store,
            )

    assert did is True
    assert result == compacted
    mock_a8.assert_awaited_once()
    assert mock_a8.await_args.kwargs["artifact_port"] is artifact_port
    assert mock_a8.await_args.kwargs["budget_store"] is budget_store
    mock_compact.assert_awaited_once()
    assert mock_compact.await_args.args[0] == [LLMMessage(role="user", content="budgeted")]
    assert mock_compact.await_args.kwargs["session_id"] == "sess-l2"
    assert mock_compact.await_args.kwargs["session_memory"] is session_memory
    assert mock_compact.await_args.kwargs["hooks"] is hooks
    assert mock_compact.await_args.kwargs["progress"] is progress


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
