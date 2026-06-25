"""Compression types and port stub tests."""

from __future__ import annotations

import pytest

from aiecs.domain.context.compression.types import (
    CompactionResult,
    ImageBlock,
    NoOpSessionMemoryPort,
    NoOpToolArtifactPort,
    NoOpToolBudgetStore,
    PostCompactContext,
    PostCompactHook,
    PreCompactContext,
    PreCompactHook,
    PreCompactResult,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    TruncationMode,
)


@pytest.mark.asyncio
async def test_noop_session_memory_port() -> None:
    port = NoOpSessionMemoryPort()
    assert await port.read_compact_text(session_id="s1") is None
    await port.write_turn_summary(session_id="s1", text="summary")


@pytest.mark.asyncio
async def test_noop_tool_artifact_port() -> None:
    port = NoOpToolArtifactPort()
    uri = await port.store_tool_output(
        session_id="s1",
        tool_call_id="call_1",
        content="payload",
    )
    assert uri == ""


def test_noop_tool_budget_store() -> None:
    store = NoOpToolBudgetStore()
    assert store.get_replacement("call_1") is None
    store.set_replacement("call_1", "preview")


def test_truncation_mode_values() -> None:
    assert TruncationMode.EARLIER_PLACEHOLDER.value == "earlier_placeholder"
    assert TruncationMode.TRUNCATE_MIDDLE.value == "truncate_middle"


def test_content_block_subtypes() -> None:
    text = TextBlock(text="hello")
    tool_use = ToolUseBlock(id="id1", name="grep", input={"pattern": "a"})
    tool_result = ToolResultBlock(tool_use_id="id1", content="done")
    image = ImageBlock(source="https://example.com/a.png")
    assert text.text == "hello"
    assert tool_use.name == "grep"
    assert tool_result.content == "done"
    assert image.source.endswith(".png")


def test_compaction_result_defaults() -> None:
    result = CompactionResult(trigger="auto", compact_kind="full")
    assert result.summary_messages == []
    assert result.compact_metadata == {}


class _PreHook:
    async def __call__(self, ctx: PreCompactContext) -> PreCompactResult:
        return PreCompactResult(append_instructions="keep tools")


class _PostHook:
    async def __call__(self, ctx: PostCompactContext) -> None:
        return None


def test_hook_protocol_stubs() -> None:
    assert isinstance(_PreHook(), PreCompactHook)
    assert isinstance(_PostHook(), PostCompactHook)
