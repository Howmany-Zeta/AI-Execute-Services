# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""L2 Multi-Task compact adapter at MC recursive boundary (CC-095).

Host calls this from ``_recursively_execute_task`` (or equivalent) when
``USE_AIECS_COMPRESSION`` is enabled. L1 warn-only and boundary *when* to
compact remain host policy.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Sequence

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.hooks import HookExecutor
from aiecs.domain.context.compression.orchestrator import auto_compact_if_needed
from aiecs.domain.context.compression.policy import (
    CompressionPolicy,
    resolve_compact_chain,
)
from aiecs.domain.context.compression.progress import CompactProgressEmitter
from aiecs.domain.context.compression.state import AutoCompactState
from aiecs.domain.context.compression.tool_budget import enforce_tool_result_budget
from aiecs.domain.context.compression.types import (
    NoOpToolBudgetStore,
    SessionMemoryPort,
    ToolArtifactPort,
    ToolBudgetStore,
)
from aiecs.host.compression.config import use_aiecs_compression


def _history_to_llm_messages(
    formatted_history: Sequence[dict[str, Any] | LLMMessage],
) -> list[LLMMessage]:
    messages: list[LLMMessage] = []
    for item in formatted_history:
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


async def compact_at_mc_recursive_boundary(
    formatted_history: Sequence[dict[str, Any] | LLMMessage],
    *,
    policy: CompressionPolicy,
    llm_client: Any,
    session_id: str = "",
    strategy: str | tuple[str, ...] | None = None,
    state: AutoCompactState | None = None,
    force: bool = False,
    session_memory: SessionMemoryPort | None = None,
    hooks: HookExecutor | None = None,
    progress: CompactProgressEmitter | None = None,
    artifact_port: ToolArtifactPort | None = None,
    budget_store: ToolBudgetStore | None = None,
) -> tuple[list[LLMMessage], bool]:
    """Run O3 compact on MC history when host L2 boundary fires.

    Returns ``(messages, did_compact)``. No-op when ``USE_AIECS_COMPRESSION`` is
    off unless *force* is True.

    Pass the same ports as L3 ``ToolLoopCompressionContext`` (session memory,
    hooks, progress, artifact/budget stores) so MC compacts persist summaries,
    emit progress, and offload tool artifacts.
    """
    if not force and not use_aiecs_compression():
        return _history_to_llm_messages(formatted_history), False

    messages = _history_to_llm_messages(formatted_history)
    compact_state = state or AutoCompactState()
    chain = resolve_compact_chain(policy, strategy)
    mc_policy = policy
    if chain != policy.chain:
        mc_policy = replace(policy, chain=chain)

    working = list(messages)
    if budget_store is not None and not isinstance(budget_store, NoOpToolBudgetStore):
        working = await enforce_tool_result_budget(
            working,
            session_id=session_id,
            budget_store=budget_store,
            artifact_port=artifact_port,
        )

    return await auto_compact_if_needed(
        working,
        policy=mc_policy,
        state=compact_state,
        llm_client=llm_client,
        session_id=session_id,
        session_memory=session_memory,
        hooks=hooks,
        progress=progress,
        strategy=strategy,
        force=force,
    )
