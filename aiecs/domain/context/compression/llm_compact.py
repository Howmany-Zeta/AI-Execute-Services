# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""W5: LLM-based conversation compact (A4)."""

from __future__ import annotations

import re
from typing import Any, Literal

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.constants import (
    ERROR_MESSAGE_INCOMPLETE_RESPONSE,
    MAX_COMPACT_STREAMING_RETRIES,
    MAX_OUTPUT_TOKENS_FOR_SUMMARY,
    MAX_PTL_RETRIES,
)
from aiecs.domain.context.compression.collapse import try_context_collapse
from aiecs.domain.context.compression.images import replace_images_for_compaction
from aiecs.domain.context.compression.microcompact import microcompact_messages
from aiecs.domain.context.compression.pairs import split_messages_preserving_tool_pairs
from aiecs.domain.context.compression.ptl import (
    is_prompt_too_long_error,
    truncate_head_for_ptl_retry,
)
from aiecs.domain.context.compression.tokens import estimate_message_tokens
from aiecs.domain.context.compression.result import (
    build_post_compact_messages,
    create_compact_boundary_message,
)
from aiecs.domain.context.compression.session_memory import (
    persist_turn_summary,
    try_session_memory_compaction,
)
from aiecs.domain.context.compression.types import (
    CompactionResult,
    CompactTrigger,
    PostCompactContext,
    PostCompactHook,
    PreCompactContext,
    PreCompactHook,
    PreCompactResult,
    SessionMemoryPort,
)

NO_TOOLS_PREAMBLE = """\
CRITICAL: Respond with TEXT ONLY. Do NOT call any tools.

- Do NOT use read_file, bash, grep, glob, edit_file, write_file, or ANY other tool.
- You already have all the context you need in the conversation above.
- Tool calls will be REJECTED and will waste your only turn — you will fail the task.
- Your entire response must be plain text: an <analysis> block followed by a <summary> block.

"""

BASE_COMPACT_PROMPT = """\
Your task is to create a detailed summary of the conversation so far. This summary will replace the earlier messages, so it must capture all important information.

First, draft your analysis inside <analysis> tags. Walk through the conversation chronologically and extract:
- Every user request and intent (explicit and implicit)
- The approach taken and technical decisions made
- Specific code, files, and configurations discussed (with paths and line numbers where available)
- All errors encountered and how they were fixed
- Any user feedback or corrections

Then, produce a structured summary inside <summary> tags with these sections:

1. **Primary Request and Intent**: All user requests in full detail, including nuances and constraints.
2. **Key Technical Concepts**: Technologies, frameworks, patterns, and conventions discussed.
3. **Files and Code Sections**: Every file examined or modified, with specific code snippets and line numbers.
4. **Errors and Fixes**: Every error encountered, its cause, and how it was resolved.
5. **Problem Solving**: Problems solved and approaches that worked vs. didn't work.
6. **All User Messages**: Non-tool-result user messages (preserve exact wording for context).
7. **Pending Tasks**: Explicitly requested work that hasn't been completed yet.
8. **Current Work**: Detailed description of the last task being worked on before compaction.
9. **Optional Next Step**: The single most logical next step, directly aligned with the user's recent request.
"""

NO_TOOLS_TRAILER = """
REMINDER: Do NOT call any tools. Respond with plain text only — an <analysis> block followed by a <summary> block. Tool calls will be rejected and you will fail the task."""


def get_compact_prompt(custom_instructions: str | None = None) -> str:
    prompt = NO_TOOLS_PREAMBLE + BASE_COMPACT_PROMPT
    if custom_instructions and custom_instructions.strip():
        prompt += f"\n\nAdditional Instructions:\n{custom_instructions}"
    prompt += NO_TOOLS_TRAILER
    return prompt


def format_compact_summary(raw_summary: str) -> str:
    text = re.sub(r"<analysis>[\s\S]*?</analysis>", "", raw_summary)
    match = re.search(r"<summary>([\s\S]*?)</summary>", text)
    if match:
        text = text.replace(match.group(0), f"Summary:\n{match.group(1).strip()}")
    text = re.sub(r"\n\n+", "\n\n", text)
    return text.strip()


def build_compact_summary_message(
    summary: str,
    *,
    suppress_follow_up: bool = False,
    recent_preserved: bool = False,
) -> str:
    formatted = format_compact_summary(summary)
    text = "This session is being continued from a previous conversation that ran " "out of context. The summary below covers the earlier portion of the " "conversation.\n\n" f"{formatted}"
    if recent_preserved:
        text += "\n\nRecent messages are preserved verbatim."
    if suppress_follow_up:
        text += (
            "\nContinue the conversation from where it left off without asking "
            "the user any further questions. Resume directly — do not acknowledge "
            "the summary, do not recap what was happening, do not preface with "
            '"I\'ll continue" or similar. Pick up the last task as if the break '
            "never happened."
        )
    return text


def _summary_text_from_result(result: CompactionResult) -> str:
    return " ".join((message.content or "").strip() for message in result.summary_messages if (message.content or "").strip())


def _build_passthrough_compaction_result(
    messages: list[LLMMessage],
    *,
    trigger: CompactTrigger,
    compact_kind: Literal["full", "session_memory"],
    metadata: dict[str, Any] | None = None,
) -> CompactionResult:
    meta = {"reason": (metadata or {}).get("reason", "passthrough"), **(metadata or {})}
    return CompactionResult(
        trigger=trigger,
        compact_kind=compact_kind,
        boundary_marker=create_compact_boundary_message(meta),
        summary_messages=[],
        messages_to_keep=list(messages),
        compact_metadata=meta,
    )


def _finalize_compaction_result(result: CompactionResult) -> CompactionResult:
    post_compact = build_post_compact_messages(result)
    result.compact_metadata.setdefault("post_compact_message_count", len(post_compact))
    result.compact_metadata.setdefault(
        "post_compact_token_count",
        estimate_message_tokens(post_compact),
    )
    result.boundary_marker = create_compact_boundary_message(result.compact_metadata)
    return result


def _prepend_system_prompt(
    messages: list[LLMMessage],
    system_prompt: str,
) -> list[LLMMessage]:
    """Inject summarizer instructions as a system message (OpenAI-compatible)."""
    if messages and messages[0].role == "system":
        return messages
    prompt = system_prompt or "You are a conversation summarizer."
    return [LLMMessage(role="system", content=prompt), *messages]


async def _summarize_old_messages(
    llm_client: Any,
    messages: list[LLMMessage],
    *,
    summary_max_tokens: int,
    system_prompt: str = "",
) -> str:
    """Call the LLM to summarize older messages (ContextEngine-compatible helper)."""
    retry_messages = list(messages)
    ptl_retries = 0
    last_exc: Exception | None = None

    for attempt in range(1, MAX_COMPACT_STREAMING_RETRIES + 2):
        try:
            response = await llm_client.generate_text(
                messages=_prepend_system_prompt(retry_messages, system_prompt),
                max_tokens=summary_max_tokens,
            )
            content = getattr(response, "content", None) or str(response)
            if content.strip():
                return content
            raise RuntimeError(ERROR_MESSAGE_INCOMPLETE_RESPONSE)
        except Exception as exc:
            last_exc = exc
            if is_prompt_too_long_error(exc) and ptl_retries < MAX_PTL_RETRIES:
                truncated = truncate_head_for_ptl_retry(retry_messages[:-1])
                if truncated:
                    ptl_retries += 1
                    retry_messages = [*truncated, retry_messages[-1]]
                    continue
            if attempt > MAX_COMPACT_STREAMING_RETRIES:
                raise
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(ERROR_MESSAGE_INCOMPLETE_RESPONSE)


async def _run_pre_compact_hook(
    hook: PreCompactHook | None,
    *,
    messages: list[LLMMessage],
    trigger: CompactTrigger,
) -> PreCompactResult:
    if hook is None:
        return PreCompactResult()
    return await hook(PreCompactContext(messages=messages, trigger=trigger))


async def _run_post_compact_hook(
    hook: PostCompactHook | None,
    *,
    result: CompactionResult,
) -> None:
    if hook is None:
        return
    await hook(
        PostCompactContext(
            summary_text=_summary_text_from_result(result),
            result=result,
        )
    )


async def compact_conversation(
    messages: list[LLMMessage],
    *,
    llm_client: Any,
    preserve_recent: int = 6,
    summary_role: Literal["user", "system"] = "user",
    custom_instructions: str | None = None,
    summary_max_tokens: int = MAX_OUTPUT_TOKENS_FOR_SUMMARY,
    suppress_follow_up: bool = True,
    trigger: CompactTrigger = "manual",
    system_prompt: str = "",
    pre_compact_hook: PreCompactHook | None = None,
    post_compact_hook: PostCompactHook | None = None,
) -> CompactionResult:
    """Compact messages by calling the LLM to produce a structured summary."""
    if len(messages) <= preserve_recent:
        return _build_passthrough_compaction_result(
            messages,
            trigger=trigger,
            compact_kind="full",
            metadata={"reason": "conversation already within preserve_recent window"},
        )

    working, tokens_freed = microcompact_messages(
        list(messages),
        keep_recent=preserve_recent,
    )
    pre_compact_tokens = estimate_message_tokens(working)
    older, newer = split_messages_preserving_tool_pairs(
        working,
        preserve_recent=preserve_recent,
    )

    hook_result = await _run_pre_compact_hook(
        pre_compact_hook,
        messages=working,
        trigger=trigger,
    )
    if hook_result.block:
        return _build_passthrough_compaction_result(
            working,
            trigger=trigger,
            compact_kind="full",
            metadata={"reason": "pre-compact hook blocked compaction"},
        )
    instructions = custom_instructions
    if hook_result.append_instructions:
        instructions = f"{instructions}\n{hook_result.append_instructions}" if instructions else hook_result.append_instructions

    compact_prompt = get_compact_prompt(instructions)
    summarize_batch = replace_images_for_compaction(list(older)) + [LLMMessage(role="user", content=compact_prompt)]
    summary_text = await _summarize_old_messages(
        llm_client,
        summarize_batch,
        summary_max_tokens=summary_max_tokens,
        system_prompt=system_prompt,
    )

    summary_content = build_compact_summary_message(
        summary_text,
        suppress_follow_up=suppress_follow_up,
        recent_preserved=len(newer) > 0,
    )
    summary_msg = LLMMessage(role=summary_role, content=summary_content)

    compact_metadata: dict[str, Any] = {
        "trigger": trigger,
        "compact_kind": "full",
        "pre_compact_message_count": len(working),
        "pre_compact_token_count": pre_compact_tokens,
        "preserve_recent": preserve_recent,
        "tokens_freed_by_microcompact": tokens_freed,
        "used_session_memory": False,
    }
    result = CompactionResult(
        trigger=trigger,
        compact_kind="full",
        boundary_marker=create_compact_boundary_message(compact_metadata),
        summary_messages=[summary_msg],
        messages_to_keep=list(newer),
        attachments=[],
        hook_results=[],
        compact_metadata=compact_metadata,
    )
    await _run_post_compact_hook(post_compact_hook, result=result)
    return _finalize_compaction_result(result)


async def run_phase2_compact_chain(
    messages: list[LLMMessage],
    *,
    llm_client: Any,
    session_memory: SessionMemoryPort | None = None,
    session_id: str = "",
    preserve_recent: int = 12,
) -> list[LLMMessage]:
    """Default Phase 2 chain: microcompact → collapse → session memory → LLM."""
    current, _ = microcompact_messages(list(messages))
    collapsed = try_context_collapse(current, preserve_recent=preserve_recent)
    if collapsed is not None:
        current = collapsed

    sm_result = await try_session_memory_compaction(
        current,
        preserve_recent=preserve_recent,
        session_memory=session_memory,
        metadata={"session_id": session_id},
    )
    if sm_result is not None:
        return build_post_compact_messages(sm_result)

    llm_result = await compact_conversation(
        current,
        llm_client=llm_client,
        preserve_recent=preserve_recent,
    )
    summary_text = _summary_text_from_result(llm_result)
    await persist_turn_summary(
        session_memory,
        session_id=session_id,
        summary_text=summary_text,
    )
    return build_post_compact_messages(llm_result)
