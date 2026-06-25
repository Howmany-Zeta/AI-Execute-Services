"""Internal CompactionResult + build_post_compact_messages tests."""

from __future__ import annotations

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.result import (
    build_post_compact_messages,
    create_compact_boundary_message,
    render_compact_attachment,
)
from aiecs.domain.context.compression.types import CompactAttachment, CompactionResult


def test_build_post_compact_messages_ordering() -> None:
    result = CompactionResult(
        trigger="manual",
        compact_kind="full",
        boundary_marker=LLMMessage(role="user", content="[Compact boundary marker]"),
        summary_messages=[LLMMessage(role="user", content="summary body")],
        messages_to_keep=[LLMMessage(role="assistant", content="recent")],
        attachments=[
            CompactAttachment(kind="recent_files", title="Files", body="file-a")
        ],
        hook_results=[
            CompactAttachment(kind="hook_results", title="Notes", body="note-a")
        ],
        compact_metadata={"trigger": "manual", "compact_kind": "full"},
    )

    rebuilt = build_post_compact_messages(result)

    assert rebuilt[0].content == "[Compact boundary marker]"
    assert rebuilt[1].content == "summary body"
    assert rebuilt[2].content == "recent"
    assert "[Compact attachment: recent_files]" in (rebuilt[3].content or "")
    assert "[Compact attachment: hook_results]" in (rebuilt[4].content or "")


def test_create_compact_boundary_message_includes_metadata() -> None:
    marker = create_compact_boundary_message(
        {
            "trigger": "auto",
            "compact_kind": "session_memory",
            "pre_compact_message_count": 10,
            "post_compact_message_count": 4,
        }
    )
    text = marker.content or ""
    assert "Compact boundary marker" in text
    assert "Trigger: auto" in text
    assert "Compaction kind: session_memory" in text


def test_render_compact_attachment() -> None:
    rendered = render_compact_attachment(
        CompactAttachment(kind="task_focus", title="Focus", body="goal: ship")
    )
    assert "[Compact attachment: task_focus]" in (rendered.content or "")
