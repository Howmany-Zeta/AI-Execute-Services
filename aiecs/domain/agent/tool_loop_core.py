# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Shared types for HybridAgent tool-loop extraction (§8.4, DAWP v2.1 DAWP-1).

``HybridAgent._run_tool_loop_with_iteration_hooks`` and DAWP StepRunner
share the same LLM+tool iteration semantics; ``ON_ITERATION_*`` hooks use ``plugin_ctx``.

Compression hooks (ADR-009, M2 W8/W11, M3 O3) live here — HybridAgent delegates.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, TYPE_CHECKING

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.orchestrator import (
    auto_compact_if_needed,
    on_prompt_too_long,
)
from aiecs.domain.context.compression.hooks import HookExecutor
from aiecs.domain.context.compression.metadata import build_pre_compact_metadata
from aiecs.domain.context.compression.policy import CompressionPolicy
from aiecs.domain.context.compression.progress import CompactProgressEmitter
from aiecs.domain.context.compression.state import AutoCompactState
from aiecs.domain.context.compression.tokens import estimate_message_tokens
from aiecs.domain.context.compression.tool_budget import (
    enforce_tool_result_budget,
    offload_tool_output_if_needed,
)
from aiecs.domain.context.compression.types import (
    NoOpToolArtifactPort,
    NoOpToolBudgetStore,
    SessionMemoryPort,
    ToolArtifactPort,
    ToolBudgetStore,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aiecs.domain.agent.plugins.context import AgentPluginContext


@dataclass
class ToolLoopRunState:
    """Mutable accumulator for one tool-loop run."""

    steps: List[Dict[str, Any]] = field(default_factory=list)
    tool_calls_count: int = 0
    total_tokens: int = 0
    last_outcome: Optional["ToolLoopIterationOutcome"] = None


@dataclass(frozen=True)
class ToolLoopIterationOutcome:
    """Result of a single tool-loop iteration (sync or streaming)."""

    kind: Literal["continue", "final", "stop_match", "max_iterations"]
    result: Optional[Dict[str, Any]] = None


@dataclass
class ToolLoopCompressionContext:
    """Ports + policy for W8/W11/O3 compression in the HybridAgent hot path."""

    enabled: bool = True
    policy: CompressionPolicy | None = None
    session_id: str = ""
    artifact_port: ToolArtifactPort | None = None
    budget_store: ToolBudgetStore | None = None
    session_memory: SessionMemoryPort | None = None
    hooks: HookExecutor | None = None
    progress: CompactProgressEmitter | None = None
    llm_client: Any | None = None
    auto_compact_state: AutoCompactState | None = None


async def apply_tool_output_management(
    *,
    tool_name: str,
    tool_call_id: str,
    tool_output: str,
    compression_ctx: ToolLoopCompressionContext,
) -> str:
    """W11d/e: offload oversized tool output before append (A9).

    Must run **before** ``messages.append`` for the tool result. Never append
    full output when offload is required.
    """
    if not compression_ctx.enabled:
        return tool_output
    port = compression_ctx.artifact_port or NoOpToolArtifactPort()
    return await offload_tool_output_if_needed(
        session_id=compression_ctx.session_id,
        tool_name=tool_name,
        tool_call_id=tool_call_id,
        output=tool_output,
        artifact_port=port,
    )


async def maybe_compact_before_llm(
    messages: list[LLMMessage],
    *,
    compression_ctx: ToolLoopCompressionContext,
    plugin_ctx: Optional["AgentPluginContext"] = None,
) -> list[LLMMessage]:
    """W8d (M3): delegate proactive compact to ``auto_compact_if_needed`` (O3).

    Order: A8 budget enforcement → O3 orchestrator. W8e fail-open on error.
    When HookPlugin is enabled, H3/H4 fire via ``bridge_compression`` (§6.7.1).
    """
    if not compression_ctx.enabled:
        return messages

    policy = compression_ctx.policy or CompressionPolicy(enabled=False)
    if not policy.enabled:
        return messages

    from aiecs.domain.agent.plugins.hooks.bridge_compression import resolve_bridged_compression_hooks

    hooks = resolve_bridged_compression_hooks(compression_ctx.hooks, plugin_ctx)

    working = list(messages)
    try:

        if compression_ctx.budget_store is not None and not isinstance(compression_ctx.budget_store, NoOpToolBudgetStore):
            working = await enforce_tool_result_budget(
                working,
                session_id=compression_ctx.session_id,
                budget_store=compression_ctx.budget_store,
                artifact_port=compression_ctx.artifact_port,
            )

        if compression_ctx.llm_client is None:
            logger.debug("Skipping auto_compact_if_needed: no llm_client")
            return working

        if compression_ctx.auto_compact_state is None:
            compression_ctx.auto_compact_state = AutoCompactState()

        compacted, _did_compact = await auto_compact_if_needed(
            working,
            policy=policy,
            state=compression_ctx.auto_compact_state,
            llm_client=compression_ctx.llm_client,
            session_id=compression_ctx.session_id,
            session_memory=compression_ctx.session_memory,
            hooks=hooks,
            progress=compression_ctx.progress,
            compact_metadata=build_pre_compact_metadata(
                layer="L3",
                session_id=compression_ctx.session_id,
                agent_id=str(getattr(plugin_ctx.agent, "agent_id", "")) if plugin_ctx is not None else "",
                formatted_transcript=False,
                estimated_tokens=estimate_message_tokens(working),
            ),
        )
        return compacted
    except Exception as exc:
        logger.warning(
            "Context compression failed (fail-open, W8e): %s",
            exc,
            exc_info=True,
        )
        return working


async def maybe_reactive_compact_on_ptl(
    exc: Exception,
    *,
    messages: list[LLMMessage],
    compression_ctx: ToolLoopCompressionContext,
) -> bool:
    """O5: reactive compact wrapper for HybridAgent LLM catch sites."""
    if not compression_ctx.enabled:
        return False
    policy = compression_ctx.policy or CompressionPolicy(enabled=False)
    if not policy.enabled or compression_ctx.llm_client is None:
        return False
    if compression_ctx.auto_compact_state is None:
        compression_ctx.auto_compact_state = AutoCompactState()
    return await on_prompt_too_long(
        exc,
        messages=messages,
        policy=policy,
        state=compression_ctx.auto_compact_state,
        llm_client=compression_ctx.llm_client,
        session_id=compression_ctx.session_id,
        session_memory=compression_ctx.session_memory,
        hooks=compression_ctx.hooks,
        progress=compression_ctx.progress,
    )
