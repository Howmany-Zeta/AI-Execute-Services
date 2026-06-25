# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Context compression kernel (Phase 0–1)."""

from aiecs.domain.context.compression.collapse import _collapse_text, try_context_collapse
from aiecs.domain.context.compression.constants import (
    AUTOCOMPACT_BUFFER_TOKENS,
    COMPACTABLE_TOOLS,
    CONTEXT_COLLAPSE_HEAD_CHARS,
    CONTEXT_COLLAPSE_TAIL_CHARS,
    CONTEXT_COLLAPSE_TEXT_CHAR_LIMIT,
    DEFAULT_TOOL_OUTPUT_INLINE_CHARS,
    DEFAULT_TOOL_OUTPUT_PREVIEW_CHARS,
    DEFAULT_TOOL_RESULTS_PER_MESSAGE_CHARS,
    MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES,
    PTL_RETRY_MARKER,
    SESSION_MEMORY_KEEP_RECENT,
    SESSION_MEMORY_MAX_CHARS,
    SESSION_MEMORY_MAX_LINES,
    TIME_BASED_MC_CLEARED_MESSAGE,
    TOKEN_ESTIMATION_PADDING,
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
from aiecs.domain.context.compression.ptl import is_prompt_too_long_error
from aiecs.domain.context.compression.images import (
    replace_images_for_compaction,
    _replace_images_with_compaction_placeholders,
)
from aiecs.domain.context.compression.hooks import HookEvent, HookExecutor, HookRegistry
from aiecs.domain.context.compression.orchestrator import (
    auto_compact_if_needed,
    on_prompt_too_long,
)
from aiecs.domain.context.compression.policy import (
    CompressionPolicy,
    get_autocompact_threshold,
    resolve_compact_chain,
    should_compress,
)
from aiecs.domain.context.compression.progress import (
    COMPACT_PROGRESS_PHASES,
    CompactProgressEmitter,
    CompactProgressEvent,
)
from aiecs.domain.context.compression.result import (
    CompactionResult,
    CompactAttachment,
    build_post_compact_messages,
)
from aiecs.domain.context.compression.state import AutoCompactState
from aiecs.domain.context.compression.microcompact import (
    is_microcompactable_tool_result,
    microcompact_messages,
)
from aiecs.domain.context.compression.pairs import (
    sanitize_messages_for_compaction,
    split_messages_preserving_tool_pairs,
    split_preserving_tool_pairs,
)
from aiecs.domain.context.compression.ptl import truncate_head_for_ptl_retry
from aiecs.domain.context.compression.tokens import (
    estimate_message_tokens,
    estimate_tokens,
    should_compress_messages,
)
from aiecs.domain.context.compression.truncation import (
    compress_preserve_recent,
    compress_to_token_limit,
    compress_with_earlier_placeholder,
    truncate_middle,
)
from aiecs.domain.context.compression.types import (
    ContentBlock,
    ImageBlock,
    NoOpSessionMemoryPort,
    InMemorySessionMemoryPort,
    NoOpToolArtifactPort,
    NoOpToolBudgetStore,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    TruncationMode,
)

__all__ = [
    "AUTOCOMPACT_BUFFER_TOKENS",
    "COMPACTABLE_TOOLS",
    "COMPACT_PROGRESS_PHASES",
    "CompactProgressEvent",
    "CompactProgressEmitter",
    "CompactionResult",
    "CompactAttachment",
    "HookEvent",
    "HookExecutor",
    "HookRegistry",
    "AutoCompactState",
    "CompressionPolicy",
    "auto_compact_if_needed",
    "resolve_compact_chain",
    "should_compress",
    "CONTEXT_COLLAPSE_HEAD_CHARS",
    "CONTEXT_COLLAPSE_TAIL_CHARS",
    "CONTEXT_COLLAPSE_TEXT_CHAR_LIMIT",
    "ContentBlock",
    "ImageBlock",
    "MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES",
    "NoOpSessionMemoryPort",
    "InMemorySessionMemoryPort",
    "NoOpToolArtifactPort",
    "NoOpToolBudgetStore",
    "PTL_RETRY_MARKER",
    "SESSION_MEMORY_KEEP_RECENT",
    "SESSION_MEMORY_MAX_CHARS",
    "SESSION_MEMORY_MAX_LINES",
    "TIME_BASED_MC_CLEARED_MESSAGE",
    "TextBlock",
    "TOKEN_ESTIMATION_PADDING",
    "TOOL_OUTPUT_TRUNCATED_HEADER",
    "ToolResultBlock",
    "DEFAULT_TOOL_OUTPUT_INLINE_CHARS",
    "DEFAULT_TOOL_OUTPUT_PREVIEW_CHARS",
    "DEFAULT_TOOL_RESULTS_PER_MESSAGE_CHARS",
    "InMemoryToolBudgetStore",
    "build_tool_output_preview",
    "enforce_tool_result_budget",
    "offload_tool_output_if_needed",
    "tool_output_inline_chars",
    "tool_output_preview_chars",
    "tool_results_per_message_chars",
    "ToolUseBlock",
    "TruncationMode",
    "_collapse_text",
    "_replace_images_with_compaction_placeholders",
    "build_post_compact_messages",
    "is_microcompactable_tool_result",
    "microcompact_messages",
    "replace_images_for_compaction",
    "sanitize_messages_for_compaction",
    "split_messages_preserving_tool_pairs",
    "split_preserving_tool_pairs",
    "truncate_head_for_ptl_retry",
    "truncate_middle",
    "try_context_collapse",
    "compress_preserve_recent",
    "compress_to_token_limit",
    "compress_with_earlier_placeholder",
    "estimate_message_tokens",
    "estimate_tokens",
    "get_autocompact_threshold",
    "should_compress_messages",
]
