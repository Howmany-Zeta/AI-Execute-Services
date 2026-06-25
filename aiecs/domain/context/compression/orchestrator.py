# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""O3–O5: auto_compact_if_needed orchestrator and reactive PTL wrapper."""

from __future__ import annotations

import logging
from typing import Any, Literal

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.collapse import try_context_collapse
from aiecs.domain.context.compression.hooks import HookExecutor
from aiecs.domain.context.compression.llm_compact import compact_conversation
from aiecs.domain.context.compression.microcompact import microcompact_messages
from aiecs.domain.context.compression.policy import (
    CompressionPolicy,
    policy_with_chain,
    resolve_compact_chain,
    should_compress,
)
from aiecs.domain.context.compression.progress import CompactProgressEmitter
from aiecs.domain.context.compression.ptl import is_prompt_too_long_error
from aiecs.domain.context.compression.result import (
    build_post_compact_messages,
    create_compact_boundary_message,
)
from aiecs.domain.context.compression.session_memory import (
    persist_turn_summary,
    try_session_memory_compaction,
)
from aiecs.domain.context.compression.state import AutoCompactState
from aiecs.domain.context.compression.tokens import estimate_message_tokens
from aiecs.domain.context.compression.types import (
    CompactionResult,
    PostCompactContext,
    PreCompactContext,
    SessionMemoryPort,
)

logger = logging.getLogger(__name__)

CompactTrigger = Literal["auto", "manual", "reactive"]


def _emit_progress(
    progress: CompactProgressEmitter | None,
    phase: str,
    *,
    pre_tokens: int | None = None,
    post_tokens: int | None = None,
    checkpoint: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    if progress is None:
        return
    progress.emit(
        phase,
        checkpoint=checkpoint,
        pre_tokens=pre_tokens,
        post_tokens=post_tokens,
        metadata=metadata,
    )


def _build_checkpoint_compaction_result(
    *,
    trigger: CompactTrigger,
    working: list[LLMMessage],
    pre_tokens: int,
    checkpoint: str,
    metadata: dict[str, Any] | None = None,
) -> CompactionResult:
    compact_metadata: dict[str, Any] = {
        "trigger": trigger,
        "compact_kind": "full",
        "checkpoint": checkpoint,
        "pre_compact_token_count": pre_tokens,
        "post_compact_token_count": estimate_message_tokens(working),
        **(metadata or {}),
    }
    return CompactionResult(
        trigger=trigger,
        compact_kind="full",
        boundary_marker=create_compact_boundary_message(compact_metadata),
        summary_messages=[],
        messages_to_keep=list(working),
        compact_metadata=compact_metadata,
    )


async def _finish_chain_early_exit(
    working: list[LLMMessage],
    *,
    pre_tokens: int,
    trigger: CompactTrigger,
    checkpoint: str,
    state: AutoCompactState,
    hooks: HookExecutor | None,
    progress: CompactProgressEmitter | None,
    metadata: dict[str, Any] | None = None,
) -> tuple[list[LLMMessage], bool]:
    post_tokens = estimate_message_tokens(working)
    state.consecutive_failures = 0
    _emit_progress(
        progress,
        "compact_done",
        pre_tokens=pre_tokens,
        post_tokens=post_tokens,
        checkpoint=checkpoint,
        metadata=metadata,
    )
    if hooks is not None:
        result = _build_checkpoint_compaction_result(
            trigger=trigger,
            working=working,
            pre_tokens=pre_tokens,
            checkpoint=checkpoint,
            metadata=metadata,
        )
        await hooks.execute_post_compact(PostCompactContext(summary_text="", result=result))
    if progress is not None:
        progress.finish_stream()
    return working, True


async def auto_compact_if_needed(
    messages: list[LLMMessage],
    *,
    policy: CompressionPolicy,
    state: AutoCompactState,
    llm_client: Any,
    session_memory: SessionMemoryPort | None = None,
    session_id: str = "",
    force: bool = False,
    trigger: CompactTrigger = "auto",
    strategy: str | tuple[str, ...] | None = None,
    hooks: HookExecutor | None = None,
    progress: CompactProgressEmitter | None = None,
) -> tuple[list[LLMMessage], bool]:
    """O3: run configurable compact chain when threshold exceeded.

    Returns ``(messages, did_compact)``. Circuit breaker skips proactive
    compacts when ``state.consecutive_failures >= policy.max_consecutive_failures``
    unless ``force=True``.
    """
    effective_policy = policy_with_chain(
        policy,
        resolve_compact_chain(policy, strategy),
    )

    if not force and not should_compress(messages, effective_policy, state=state):
        return messages, False

    if not force and state.consecutive_failures >= effective_policy.max_consecutive_failures:
        logger.warning(
            "Skipping proactive auto-compact: consecutive_failures=%d >= max=%d",
            state.consecutive_failures,
            effective_policy.max_consecutive_failures,
        )
        return messages, False

    state.last_trigger = trigger
    working = list(messages)
    pre_tokens = estimate_message_tokens(working)

    try:
        if hooks is not None and hooks.registry.pre_hooks:
            _emit_progress(progress, "hooks_start", pre_tokens=pre_tokens)
            hook_result = await hooks.execute_pre_compact(PreCompactContext(messages=working, trigger=trigger))
            if hook_result.block:
                logger.info("Pre-compact hook blocked compaction (trigger=%s)", trigger)
                return working, False
            if hook_result.append_instructions:
                working.append(
                    LLMMessage(
                        role="user",
                        content=hook_result.append_instructions,
                    )
                )

        for step in effective_policy.chain:
            if step == "microcompact":
                _emit_progress(
                    progress,
                    "microcompact_start",
                    pre_tokens=pre_tokens,
                    checkpoint="microcompact",
                )
                working, tokens_freed = microcompact_messages(
                    working,
                    keep_recent=effective_policy.preserve_recent,
                )
                post_tokens = estimate_message_tokens(working)
                _emit_progress(
                    progress,
                    "microcompact_done",
                    pre_tokens=pre_tokens,
                    post_tokens=post_tokens,
                    metadata={"tokens_freed": tokens_freed},
                )
                if tokens_freed > 0 and not force and not should_compress(working, effective_policy, state=state):
                    return await _finish_chain_early_exit(
                        working,
                        pre_tokens=pre_tokens,
                        trigger=trigger,
                        checkpoint="microcompact_early_exit",
                        state=state,
                        hooks=hooks,
                        progress=progress,
                        metadata={"tokens_freed": tokens_freed},
                    )

            elif step == "collapse":
                _emit_progress(
                    progress,
                    "context_collapse_start",
                    pre_tokens=estimate_message_tokens(working),
                    checkpoint="collapse",
                )
                collapsed = try_context_collapse(
                    working,
                    preserve_recent=effective_policy.preserve_recent,
                )
                if collapsed is not None:
                    working = collapsed
                    post_tokens = estimate_message_tokens(working)
                    _emit_progress(
                        progress,
                        "context_collapse_done",
                        pre_tokens=pre_tokens,
                        post_tokens=post_tokens,
                    )
                    if not force and not should_compress(working, effective_policy, state=state):
                        return await _finish_chain_early_exit(
                            working,
                            pre_tokens=pre_tokens,
                            trigger=trigger,
                            checkpoint="collapse_early_exit",
                            state=state,
                            hooks=hooks,
                            progress=progress,
                        )
                else:
                    _emit_progress(
                        progress,
                        "context_collapse_done",
                        pre_tokens=pre_tokens,
                        post_tokens=estimate_message_tokens(working),
                        metadata={"skipped": True},
                    )

            elif step == "session_memory":
                _emit_progress(
                    progress,
                    "session_memory_start",
                    pre_tokens=estimate_message_tokens(working),
                    checkpoint="session_memory",
                )
                sm_result = await try_session_memory_compaction(
                    working,
                    preserve_recent=effective_policy.preserve_recent,
                    trigger=trigger,
                    session_memory=session_memory,
                    metadata={"session_id": session_id},
                )
                post_tokens = estimate_message_tokens(working)
                if sm_result is not None:
                    compacted = build_post_compact_messages(sm_result)
                    _emit_progress(
                        progress,
                        "session_memory_done",
                        pre_tokens=pre_tokens,
                        post_tokens=estimate_message_tokens(compacted),
                    )
                    _emit_progress(
                        progress,
                        "compact_done",
                        pre_tokens=pre_tokens,
                        post_tokens=estimate_message_tokens(compacted),
                        checkpoint="session_memory",
                    )
                    state.consecutive_failures = 0
                    summary_text = " ".join((msg.content or "") for msg in sm_result.summary_messages)
                    if hooks is not None:
                        await hooks.execute_post_compact(
                            PostCompactContext(
                                summary_text=summary_text,
                                result=sm_result,
                            )
                        )
                    await persist_turn_summary(
                        session_memory,
                        session_id=session_id,
                        summary_text=summary_text,
                    )
                    if progress is not None:
                        progress.finish_stream()
                    return compacted, True
                _emit_progress(
                    progress,
                    "session_memory_done",
                    pre_tokens=pre_tokens,
                    post_tokens=post_tokens,
                    metadata={"skipped": True},
                )

            elif step == "llm":
                _emit_progress(
                    progress,
                    "compact_start",
                    pre_tokens=estimate_message_tokens(working),
                    checkpoint="llm",
                )
                llm_result = await compact_conversation(
                    working,
                    llm_client=llm_client,
                    preserve_recent=effective_policy.preserve_recent,
                    summary_role=effective_policy.summary_role,
                    trigger=trigger,
                )
                compacted = build_post_compact_messages(llm_result)
                summary_text = " ".join((msg.content or "") for msg in llm_result.summary_messages)
                if hooks is not None:
                    await hooks.execute_post_compact(
                        PostCompactContext(
                            summary_text=summary_text,
                            result=llm_result,
                        )
                    )
                await persist_turn_summary(
                    session_memory,
                    session_id=session_id,
                    summary_text=summary_text,
                )
                _emit_progress(
                    progress,
                    "compact_done",
                    pre_tokens=pre_tokens,
                    post_tokens=estimate_message_tokens(compacted),
                    checkpoint="llm",
                )
                state.consecutive_failures = 0
                if progress is not None:
                    progress.finish_stream()
                return compacted, True

            else:
                logger.debug("Unknown compact chain step %r — skipping", step)

        state.consecutive_failures = 0
        if progress is not None:
            progress.finish_stream()
        return working, False
    except Exception as exc:
        state.consecutive_failures += 1
        _emit_progress(
            progress,
            "compact_failed",
            pre_tokens=pre_tokens,
            metadata={"error": str(exc), "trigger": trigger},
        )
        if progress is not None:
            progress.finish_stream()
        logger.error(
            "Auto-compact failed (attempt %d/%d, trigger=%s): %s",
            state.consecutive_failures,
            effective_policy.max_consecutive_failures,
            trigger,
            exc,
            exc_info=True,
        )
        return working, False


async def on_prompt_too_long(
    exc: Exception,
    *,
    messages: list[LLMMessage],
    policy: CompressionPolicy,
    state: AutoCompactState,
    llm_client: Any,
    session_memory: SessionMemoryPort | None = None,
    session_id: str = "",
    hooks: HookExecutor | None = None,
    progress: CompactProgressEmitter | None = None,
) -> bool:
    """O5: reactive compact once per session after PTL; returns True if compacted."""
    if not is_prompt_too_long_error(exc):
        return False
    if state.reactive_compact_used:
        return False
    state.reactive_compact_used = True
    compacted, did_compact = await auto_compact_if_needed(
        messages,
        policy=policy,
        state=state,
        llm_client=llm_client,
        session_memory=session_memory,
        session_id=session_id,
        force=True,
        trigger="reactive",
        hooks=hooks,
        progress=progress,
    )
    if did_compact:
        messages[:] = compacted
    return did_compact
