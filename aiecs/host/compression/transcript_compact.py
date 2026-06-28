# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""L2 formatted transcript compact API (Epic 3 F1).

Prefer :func:`compact_formatted_transcript` for MC formatted history rows.
:func:`aiecs.host.compression.compact_at_mc_recursive_boundary` with
``strategy="summarize"`` may still run microcompact via legacy chain resolution.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any, Sequence

from aiecs.domain.context.compression.metadata import LAYER_L2, build_pre_compact_metadata
from aiecs.domain.context.compression.orchestrator import auto_compact_if_needed
from aiecs.domain.context.compression.policy import CompressionPolicy
from aiecs.domain.context.compression.policy_resolver import resolve_layer_compression_policy
from aiecs.domain.context.compression.state import AutoCompactState
from aiecs.domain.context.compression.tokens import estimate_transcript_tokens
from aiecs.domain.context.compression.types import SessionMemoryPort
from aiecs.domain.context.compression.hooks import HookExecutor
from aiecs.domain.context.compression.progress import CompactProgressEmitter
from aiecs.llm import LLMMessage

if TYPE_CHECKING:
    from aiecs.domain.agent.models import AgentConfiguration

# F1-04: prefer this API over ``compact_at_mc_recursive_boundary(..., strategy="summarize")``
# which still resolves legacy chains that may include microcompact.


def _transcript_to_llm_messages(
    transcript: Sequence[dict[str, Any] | LLMMessage],
) -> list[LLMMessage]:
    messages: list[LLMMessage] = []
    for item in transcript:
        if isinstance(item, LLMMessage):
            messages.append(item)
            continue
        if not isinstance(item, dict):
            continue
        messages.append(
            LLMMessage(
                role=str(item.get("role", "user")),
                content=item.get("content"),
                tool_calls=item.get("tool_calls"),
                tool_call_id=item.get("tool_call_id"),
            )
        )
    return messages


def _llm_messages_to_transcript(messages: Sequence[LLMMessage]) -> list[dict[str, Any]]:
    """Preserve ``{role, content}`` dict shape (F1-03)."""
    rows: list[dict[str, Any]] = []
    for message in messages:
        row: dict[str, Any] = {
            "role": message.role,
            "content": message.content,
        }
        if message.tool_calls:
            row["tool_calls"] = message.tool_calls
        if message.tool_call_id:
            row["tool_call_id"] = message.tool_call_id
        rows.append(row)
    return rows


async def compact_formatted_transcript(
    transcript: Sequence[dict[str, Any] | LLMMessage],
    *,
    policy: CompressionPolicy | None = None,
    llm_client: Any,
    session_id: str = "",
    agent_id: str = "",
    state: AutoCompactState | None = None,
    force: bool = False,
    hooks: HookExecutor | None = None,
    progress: CompactProgressEmitter | None = None,
    session_memory: SessionMemoryPort | None = None,
    context: dict[str, Any] | None = None,
    config: AgentConfiguration | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """
    Compact formatted MC history rows at L2 (F1-01).

    Default chain is ``("llm",)`` only — inequivalent to L3 full chain (F1-03).
    """
    messages = _transcript_to_llm_messages(transcript)
    effective_policy = policy or CompressionPolicy()
    if context is not None and config is not None:
        effective_policy = await resolve_layer_compression_policy(
            LAYER_L2,
            context=context,
            config=config,
            base_policy=effective_policy,
        )
    l2_policy = replace(effective_policy, chain=("llm",))

    compact_metadata = build_pre_compact_metadata(
        layer=LAYER_L2,
        session_id=session_id,
        agent_id=agent_id,
        formatted_transcript=True,
        estimated_tokens=estimate_transcript_tokens(_llm_messages_to_transcript(messages)),
    )

    compacted, did_compact = await auto_compact_if_needed(
        messages,
        policy=l2_policy,
        state=state or AutoCompactState(),
        llm_client=llm_client,
        session_id=session_id,
        session_memory=session_memory,
        force=force,
        hooks=hooks,
        progress=progress,
        compact_metadata=compact_metadata,
    )
    return _llm_messages_to_transcript(compacted), did_compact
