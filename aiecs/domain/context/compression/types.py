# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Compression kernel types, ports, and hook protocol stubs (ADR-011)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, Protocol, runtime_checkable


class TruncationMode(str, Enum):
    """Truncation strategy for head-drop / middle truncation (ADR-003)."""

    EARLIER_PLACEHOLDER = "earlier_placeholder"
    TRUNCATE_MIDDLE = "truncate_middle"


@dataclass(frozen=True)
class TextBlock:
    text: str


@dataclass(frozen=True)
class ToolUseBlock:
    id: str
    name: str
    input: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResultBlock:
    tool_use_id: str
    content: str
    is_error: bool = False


@dataclass(frozen=True)
class ImageBlock:
    source: str
    media_type: str | None = None
    source_path: str = ""


ContentBlock = TextBlock | ToolUseBlock | ToolResultBlock | ImageBlock

CompactTrigger = Literal["auto", "manual", "reactive"]
CompactionKind = Literal["full", "session_memory"]


@dataclass
class CompactAttachment:
    kind: str
    title: str
    body: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CompactionResult:
    """Internal compaction result shape (public export via result.py O9)."""

    trigger: CompactTrigger
    compact_kind: CompactionKind
    boundary_marker: Any | None = None
    summary_messages: list[Any] = field(default_factory=list)
    messages_to_keep: list[Any] = field(default_factory=list)
    attachments: list[CompactAttachment] = field(default_factory=list)
    hook_results: list[CompactAttachment] = field(default_factory=list)
    compact_metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class SessionMemoryPort(Protocol):
    async def read_compact_text(self, *, session_id: str) -> str | None: ...

    async def write_turn_summary(self, *, session_id: str, text: str) -> None: ...


@runtime_checkable
class ToolArtifactPort(Protocol):
    async def store_tool_output(self, *, session_id: str, tool_call_id: str, content: str) -> str: ...


@runtime_checkable
class ToolBudgetStore(Protocol):
    def get_replacement(self, tool_call_id: str) -> str | None: ...

    def set_replacement(self, tool_call_id: str, preview: str) -> None: ...

    def mark_seen(self, tool_call_id: str) -> None: ...

    def is_seen(self, tool_call_id: str) -> bool: ...


class NoOpSessionMemoryPort:
    async def read_compact_text(self, *, session_id: str) -> str | None:
        return None

    async def write_turn_summary(self, *, session_id: str, text: str) -> None:
        return None


class InMemorySessionMemoryPort:
    """Per-session compact text store for A15 on HybridAgent L3 (in-process)."""

    def __init__(self) -> None:
        self._compact_text_by_session: dict[str, str] = {}

    async def read_compact_text(self, *, session_id: str) -> str | None:
        return self._compact_text_by_session.get(session_id)

    async def write_turn_summary(self, *, session_id: str, text: str) -> None:
        self._compact_text_by_session[session_id] = text


class NoOpToolArtifactPort:
    async def store_tool_output(self, *, session_id: str, tool_call_id: str, content: str) -> str:
        return ""


class NoOpToolBudgetStore:
    def get_replacement(self, tool_call_id: str) -> str | None:
        return None

    def set_replacement(self, tool_call_id: str, preview: str) -> None:
        return None

    def mark_seen(self, tool_call_id: str) -> None:
        return None

    def is_seen(self, tool_call_id: str) -> bool:
        return False


@dataclass
class PreCompactContext:
    messages: list[Any]
    trigger: CompactTrigger = "auto"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PreCompactResult:
    block: bool = False
    append_instructions: str | None = None


@dataclass
class PostCompactContext:
    summary_text: str = ""
    result: CompactionResult | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class PreCompactHook(Protocol):
    async def __call__(self, ctx: PreCompactContext) -> PreCompactResult: ...


@runtime_checkable
class PostCompactHook(Protocol):
    async def __call__(self, ctx: PostCompactContext) -> None: ...
