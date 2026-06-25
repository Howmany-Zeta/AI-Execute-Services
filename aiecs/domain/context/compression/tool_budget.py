# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""W11: Tool output offload (A9) and aggregate tool-result budget (A8).

Reference (read-only):
- OpenHarness ``engine/query.py`` ``_offload_tool_output_if_needed``
- OpenHarness ``services/tool_outputs.py`` inline/preview thresholds
- Claude ``utils/toolResultStorage.ts`` ``enforceToolResultBudget``

Artifact preview shape (inline stub returned to the model)::

    [Tool output truncated]
    Tool: {tool_name}
    Tool use id: {tool_call_id}
    Original size: {N} chars
    Full output saved to: {artifact_uri}   # omitted when ToolArtifactPort returns ""
    Inline preview: first {M} chars ({K} chars omitted)

    Preview:
    {preview_text}

Port rules (ADR-002): full tool output is stored only via ``ToolArtifactPort``;
the kernel never writes artifact files directly.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Sequence

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.constants import (
    DEFAULT_TOOL_OUTPUT_INLINE_CHARS,
    DEFAULT_TOOL_OUTPUT_PREVIEW_CHARS,
    DEFAULT_TOOL_RESULTS_PER_MESSAGE_CHARS,
    PERSISTED_OUTPUT_TAG,
    TOOL_OUTPUT_TRUNCATED_HEADER,
)
from aiecs.domain.context.compression.types import (
    NoOpToolArtifactPort,
    NoOpToolBudgetStore,
    ToolArtifactPort,
    ToolBudgetStore,
)

log = logging.getLogger(__name__)

_ENV_INLINE_CHARS = "AIECS_TOOL_OUTPUT_INLINE_CHARS"
_ENV_PREVIEW_CHARS = "AIECS_TOOL_OUTPUT_PREVIEW_CHARS"
_ENV_MESSAGE_BUDGET = "AIECS_TOOL_RESULTS_PER_MESSAGE_CHARS"


def _read_positive_int_env(name: str, default: int, *, minimum: int = 1) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(minimum, int(raw))
    except ValueError:
        log.warning("Ignoring invalid %s=%r", name, raw)
        return default


def tool_output_inline_chars() -> int:
    """Max tool output chars kept inline before offload (A9). Default 16_000."""
    return _read_positive_int_env(
        _ENV_INLINE_CHARS,
        DEFAULT_TOOL_OUTPUT_INLINE_CHARS,
        minimum=256,
    )


def tool_output_preview_chars() -> int:
    """Preview head size after offload (A9). Default 3_000."""
    return _read_positive_int_env(
        _ENV_PREVIEW_CHARS,
        DEFAULT_TOOL_OUTPUT_PREVIEW_CHARS,
        minimum=128,
    )


def tool_results_per_message_chars() -> int:
    """Aggregate tool-result char budget per message group (A8). Default 200_000."""
    return _read_positive_int_env(
        _ENV_MESSAGE_BUDGET,
        DEFAULT_TOOL_RESULTS_PER_MESSAGE_CHARS,
        minimum=1_024,
    )


def _safe_tool_name(tool_name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "_", tool_name.strip())
    return (normalized or "tool")[:80]


def _is_already_offloaded(content: str) -> bool:
    return content.startswith(TOOL_OUTPUT_TRUNCATED_HEADER) or content.startswith(PERSISTED_OUTPUT_TAG)


def build_tool_output_preview(
    *,
    tool_name: str,
    tool_call_id: str,
    output: str,
    artifact_uri: str = "",
    preview_chars: int | None = None,
) -> str:
    """Build the inline preview stub shown to the model after offload."""
    limit = preview_chars if preview_chars is not None else tool_output_preview_chars()
    preview = output[:limit]
    omitted = max(0, len(output) - len(preview))
    lines = [
        TOOL_OUTPUT_TRUNCATED_HEADER,
        f"Tool: {_safe_tool_name(tool_name)}",
        f"Tool use id: {tool_call_id}",
        f"Original size: {len(output)} chars",
    ]
    if artifact_uri:
        lines.append(f"Full output saved to: {artifact_uri}")
    preview_line = f"Inline preview: first {len(preview)} chars"
    if omitted:
        preview_line += f" ({omitted} chars omitted)"
    lines.append(preview_line)
    if preview:
        lines.extend(["", "Preview:", preview])
    return "\n".join(lines)


async def offload_tool_output_if_needed(
    *,
    session_id: str,
    tool_name: str,
    tool_call_id: str,
    output: str,
    artifact_port: ToolArtifactPort | None = None,
    max_inline_chars: int | None = None,
    preview_chars: int | None = None,
) -> str:
    """Offload oversized tool output via ``ToolArtifactPort`` (A9).

    When ``len(output) <= max_inline_chars``, returns ``output`` unchanged.
    Otherwise stores the full payload through the port and returns a bounded
    preview stub. ``NoOpToolArtifactPort`` still truncates inline (no URI).
    """
    if output is None:
        return ""
    inline_limit = max_inline_chars if max_inline_chars is not None else tool_output_inline_chars()
    if len(output) <= inline_limit:
        return output

    port = artifact_port or NoOpToolArtifactPort()
    artifact_uri = await port.store_tool_output(
        session_id=session_id,
        tool_call_id=tool_call_id,
        content=output,
    )
    return build_tool_output_preview(
        tool_name=tool_name,
        tool_call_id=tool_call_id,
        output=output,
        artifact_uri=artifact_uri,
        preview_chars=preview_chars,
    )


@dataclass
class ToolBudgetSessionState:
    """In-memory cross-turn replacement state for A8 (prompt-cache stable)."""

    seen_ids: set[str] = field(default_factory=set)
    replacements: dict[str, str] = field(default_factory=dict)


class InMemoryToolBudgetStore:
    """Memory-backed ``ToolBudgetStore`` with seen-id tracking for A8."""

    def __init__(self, state: ToolBudgetSessionState | None = None) -> None:
        self._state = state or ToolBudgetSessionState()

    @property
    def state(self) -> ToolBudgetSessionState:
        return self._state

    def get_replacement(self, tool_call_id: str) -> str | None:
        return self._state.replacements.get(tool_call_id)

    def set_replacement(self, tool_call_id: str, preview: str) -> None:
        self._state.replacements[tool_call_id] = preview
        self._state.seen_ids.add(tool_call_id)

    def mark_seen(self, tool_call_id: str) -> None:
        self._state.seen_ids.add(tool_call_id)

    def is_seen(self, tool_call_id: str) -> bool:
        return tool_call_id in self._state.seen_ids


@dataclass(frozen=True)
class _ToolResultCandidate:
    index: int
    tool_call_id: str
    tool_name: str
    content: str
    size: int


def _build_tool_name_map(messages: Sequence[LLMMessage]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for message in messages:
        if not message.tool_calls:
            continue
        for call in message.tool_calls:
            call_id = call.get("id")
            function = call.get("function") or {}
            name = function.get("name") if isinstance(function, dict) else None
            if isinstance(call_id, str) and isinstance(name, str):
                mapping[call_id] = name
    return mapping


def _collect_tool_result_groups(messages: Sequence[LLMMessage]) -> list[list[_ToolResultCandidate]]:
    """Group consecutive ``role=tool`` messages (one wire-level user batch)."""
    groups: list[list[_ToolResultCandidate]] = []
    current: list[_ToolResultCandidate] = []
    name_by_id = _build_tool_name_map(messages)

    for index, message in enumerate(messages):
        if message.role != "tool" or not message.tool_call_id:
            if current:
                groups.append(current)
                current = []
            continue
        content = message.content or ""
        if not content.strip() or _is_already_offloaded(content):
            continue
        current.append(
            _ToolResultCandidate(
                index=index,
                tool_call_id=message.tool_call_id,
                tool_name=name_by_id.get(message.tool_call_id, "tool"),
                content=content,
                size=len(content),
            )
        )

    if current:
        groups.append(current)
    return groups


def _partition_candidates(
    candidates: Sequence[_ToolResultCandidate],
    store: ToolBudgetStore,
) -> tuple[list[tuple[_ToolResultCandidate, str]], list[_ToolResultCandidate], list[_ToolResultCandidate]]:
    must_reapply: list[tuple[_ToolResultCandidate, str]] = []
    frozen: list[_ToolResultCandidate] = []
    fresh: list[_ToolResultCandidate] = []
    for candidate in candidates:
        replacement = store.get_replacement(candidate.tool_call_id)
        if replacement is not None:
            must_reapply.append((candidate, replacement))
        elif store.is_seen(candidate.tool_call_id):
            frozen.append(candidate)
        else:
            fresh.append(candidate)
    return must_reapply, frozen, fresh


def _select_fresh_to_replace(
    fresh: Sequence[_ToolResultCandidate],
    *,
    frozen_size: int,
    limit: int,
) -> list[_ToolResultCandidate]:
    sorted_fresh = sorted(fresh, key=lambda item: item.size, reverse=True)
    selected: list[_ToolResultCandidate] = []
    remaining = frozen_size + sum(item.size for item in fresh)
    for candidate in sorted_fresh:
        if remaining <= limit:
            break
        selected.append(candidate)
        remaining -= candidate.size
    return selected


async def enforce_tool_result_budget(
    messages: list[LLMMessage],
    *,
    session_id: str = "",
    budget_store: ToolBudgetStore | None = None,
    artifact_port: ToolArtifactPort | None = None,
    per_message_char_limit: int | None = None,
    skip_tool_names: frozenset[str] | None = None,
) -> list[LLMMessage]:
    """Enforce aggregate tool-result budget with stable cross-turn previews (A8).

    Uses any ``ToolBudgetStore`` with ``mark_seen`` / ``is_seen`` for cross-turn
    preview stability. ``NoOpToolBudgetStore`` disables enforcement.
    """
    if isinstance(budget_store, NoOpToolBudgetStore) or budget_store is None:
        return messages

    limit = per_message_char_limit if per_message_char_limit is not None else tool_results_per_message_chars()
    skip_names = skip_tool_names or frozenset()
    port = artifact_port or NoOpToolArtifactPort()
    replacement_by_id: dict[str, str] = {}
    result = list(messages)

    for group in _collect_tool_result_groups(messages):
        must_reapply, frozen, fresh = _partition_candidates(group, budget_store)
        for candidate, replacement in must_reapply:
            replacement_by_id[candidate.tool_call_id] = replacement

        eligible = [c for c in fresh if c.tool_name not in skip_names]
        for candidate in fresh:
            if candidate.tool_name in skip_names:
                budget_store.mark_seen(candidate.tool_call_id)

        frozen_size = sum(item.size for item in frozen)
        fresh_size = sum(item.size for item in eligible)
        selected = _select_fresh_to_replace(eligible, frozen_size=frozen_size, limit=limit) if frozen_size + fresh_size > limit else []
        selected_ids = {item.tool_call_id for item in selected}
        for candidate in group:
            if candidate.tool_call_id not in selected_ids:
                budget_store.mark_seen(candidate.tool_call_id)

        for candidate in selected:
            artifact_uri = await port.store_tool_output(
                session_id=session_id,
                tool_call_id=candidate.tool_call_id,
                content=candidate.content,
            )
            preview = build_tool_output_preview(
                tool_name=candidate.tool_name,
                tool_call_id=candidate.tool_call_id,
                output=candidate.content,
                artifact_uri=artifact_uri,
            )
            replacement_by_id[candidate.tool_call_id] = preview
            budget_store.set_replacement(candidate.tool_call_id, preview)

    if not replacement_by_id:
        return messages

    for index, message in enumerate(result):
        if message.role != "tool" or not message.tool_call_id:
            continue
        preview_text = replacement_by_id.get(message.tool_call_id)
        if preview_text is None:
            continue
        result[index] = LLMMessage(
            role=message.role,
            content=preview_text,
            tool_call_id=message.tool_call_id,
            images=message.images,
            tool_calls=message.tool_calls,
            cache_control=message.cache_control,
        )
    return result
