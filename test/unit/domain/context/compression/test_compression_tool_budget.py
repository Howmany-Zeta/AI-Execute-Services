"""W11 tool output offload (A9) and aggregate budget (A8) tests."""

from __future__ import annotations

import pytest

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.constants import (
    DEFAULT_TOOL_OUTPUT_INLINE_CHARS,
    DEFAULT_TOOL_OUTPUT_PREVIEW_CHARS,
    TOOL_OUTPUT_TRUNCATED_HEADER,
)
from aiecs.domain.context.compression.tool_budget import (
    InMemoryToolBudgetStore,
    build_tool_output_preview,
    enforce_tool_result_budget,
    offload_tool_output_if_needed,
    tool_output_inline_chars,
    tool_output_preview_chars,
    tool_results_per_message_chars,
)
from aiecs.domain.context.compression.types import NoOpToolArtifactPort


class _RecordingArtifactPort:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    async def store_tool_output(
        self, *, session_id: str, tool_call_id: str, content: str
    ) -> str:
        self.calls.append((session_id, tool_call_id, content))
        return f"artifact://{session_id}/{tool_call_id}"


def test_constants_defaults_match_openharness() -> None:
    assert DEFAULT_TOOL_OUTPUT_INLINE_CHARS == 16_000
    assert DEFAULT_TOOL_OUTPUT_PREVIEW_CHARS == 3_000
    assert tool_results_per_message_chars() == 200_000


def test_inline_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIECS_TOOL_OUTPUT_INLINE_CHARS", "512")
    monkeypatch.setenv("AIECS_TOOL_OUTPUT_PREVIEW_CHARS", "128")
    assert tool_output_inline_chars() == 512
    assert tool_output_preview_chars() == 128


@pytest.mark.asyncio
async def test_offload_below_limit_unchanged() -> None:
    output = "small result"
    result = await offload_tool_output_if_needed(
        session_id="sess-1",
        tool_name="read_file",
        tool_call_id="call_small",
        output=output,
        max_inline_chars=256,
    )
    assert result == output


@pytest.mark.asyncio
async def test_offload_above_limit_uses_port_and_preview() -> None:
    port = _RecordingArtifactPort()
    output = "line\n" * 200
    result = await offload_tool_output_if_needed(
        session_id="sess-1",
        tool_name="mcp__playwright__browser_snapshot",
        tool_call_id="toolu_snapshot",
        output=output,
        artifact_port=port,
        max_inline_chars=256,
        preview_chars=128,
    )

    assert result.startswith(TOOL_OUTPUT_TRUNCATED_HEADER)
    assert "Tool: mcp__playwright__browser_snapshot" in result
    assert "toolu_snapshot" in result
    assert "artifact://sess-1/toolu_snapshot" in result
    assert "Preview:" in result
    assert result.count("line") < 40
    assert len(port.calls) == 1
    assert port.calls[0][2] == output


@pytest.mark.asyncio
async def test_offload_noop_port_still_truncates_inline() -> None:
    output = "x" * 512
    result = await offload_tool_output_if_needed(
        session_id="sess-1",
        tool_name="bash",
        tool_call_id="call_bash",
        output=output,
        artifact_port=NoOpToolArtifactPort(),
        max_inline_chars=256,
        preview_chars=64,
    )

    assert result.startswith(TOOL_OUTPUT_TRUNCATED_HEADER)
    assert "Full output saved to:" not in result
    assert len(result) < len(output)


def test_build_tool_output_preview_shape_documented() -> None:
    preview = build_tool_output_preview(
        tool_name="grep",
        tool_call_id="call_grep",
        output="match\n" * 50,
        artifact_uri="s3://bucket/key",
        preview_chars=32,
    )
    assert preview.splitlines()[0] == TOOL_OUTPUT_TRUNCATED_HEADER
    assert "Tool: grep" in preview
    assert "Full output saved to: s3://bucket/key" in preview
    assert "Inline preview: first 32 chars" in preview


def _tool_batch_messages(
    *,
    call_a: str = "call_a",
    call_b: str = "call_b",
    size_a: int = 120_000,
    size_b: int = 120_000,
) -> list[LLMMessage]:
    return [
        LLMMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": call_a,
                    "type": "function",
                    "function": {"name": "read_file", "arguments": "{}"},
                },
                {
                    "id": call_b,
                    "type": "function",
                    "function": {"name": "grep", "arguments": "{}"},
                },
            ],
        ),
        LLMMessage(role="tool", content="A" * size_a, tool_call_id=call_a),
        LLMMessage(role="tool", content="B" * size_b, tool_call_id=call_b),
    ]


@pytest.mark.asyncio
async def test_enforce_budget_replaces_largest_fresh_results() -> None:
    port = _RecordingArtifactPort()
    store = InMemoryToolBudgetStore()
    messages = _tool_batch_messages()

    updated = await enforce_tool_result_budget(
        messages,
        session_id="sess-budget",
        budget_store=store,
        artifact_port=port,
        per_message_char_limit=200_000,
    )

    contents = {
        msg.tool_call_id: msg.content
        for msg in updated
        if msg.role == "tool" and msg.tool_call_id
    }
    assert contents["call_a"].startswith(TOOL_OUTPUT_TRUNCATED_HEADER)
    assert contents["call_b"] == "B" * 120_000
    assert len(port.calls) == 1
    assert port.calls[0][1] == "call_a"


@pytest.mark.asyncio
async def test_enforce_budget_reapplies_cached_replacement() -> None:
    store = InMemoryToolBudgetStore()
    messages = _tool_batch_messages(size_a=120_000, size_b=10_000)

    first = await enforce_tool_result_budget(
        messages,
        session_id="sess-budget",
        budget_store=store,
        artifact_port=_RecordingArtifactPort(),
        per_message_char_limit=200_000,
    )
    first_preview = next(
        msg.content
        for msg in first
        if msg.role == "tool" and msg.tool_call_id == "call_a"
    )

    second = await enforce_tool_result_budget(
        messages,
        session_id="sess-budget",
        budget_store=store,
        artifact_port=_RecordingArtifactPort(),
        per_message_char_limit=200_000,
    )
    second_preview = next(
        msg.content
        for msg in second
        if msg.role == "tool" and msg.tool_call_id == "call_a"
    )
    assert second_preview == first_preview


@pytest.mark.asyncio
async def test_enforce_budget_frozen_results_not_replaced_later() -> None:
    store = InMemoryToolBudgetStore()
    messages = _tool_batch_messages(size_a=50_000, size_b=50_000)

    await enforce_tool_result_budget(
        messages,
        session_id="sess-budget",
        budget_store=store,
        per_message_char_limit=200_000,
    )

    larger = _tool_batch_messages(size_a=150_000, size_b=150_000)
    updated = await enforce_tool_result_budget(
        larger,
        session_id="sess-budget",
        budget_store=store,
        per_message_char_limit=200_000,
    )

    frozen_content = next(
        msg.content
        for msg in updated
        if msg.role == "tool" and msg.tool_call_id == "call_a"
    )
    assert frozen_content == "A" * 150_000


@pytest.mark.asyncio
async def test_enforce_budget_noop_store_is_noop() -> None:
    from aiecs.domain.context.compression.types import NoOpToolBudgetStore

    messages = _tool_batch_messages()
    updated = await enforce_tool_result_budget(
        messages,
        budget_store=NoOpToolBudgetStore(),
    )
    assert updated == messages


class _CustomToolBudgetStore:
    """Host Redis/PG adapter shape: implements ToolBudgetStore without InMemory."""

    def __init__(self) -> None:
        self._replacements: dict[str, str] = {}
        self._seen: set[str] = set()

    def get_replacement(self, tool_call_id: str) -> str | None:
        return self._replacements.get(tool_call_id)

    def set_replacement(self, tool_call_id: str, preview: str) -> None:
        self._replacements[tool_call_id] = preview

    def mark_seen(self, tool_call_id: str) -> None:
        self._seen.add(tool_call_id)

    def is_seen(self, tool_call_id: str) -> bool:
        return tool_call_id in self._seen


@pytest.mark.asyncio
async def test_enforce_budget_accepts_custom_tool_budget_store() -> None:
    store = _CustomToolBudgetStore()
    messages = _tool_batch_messages(size_a=150_000, size_b=150_000)

    updated = await enforce_tool_result_budget(
        messages,
        session_id="sess-custom",
        budget_store=store,
        artifact_port=_RecordingArtifactPort(),
        per_message_char_limit=200_000,
    )

    tool_contents = [
        msg.content or ""
        for msg in updated
        if msg.role == "tool"
    ]
    assert any("truncated" in content.lower() for content in tool_contents)
    assert store._replacements
