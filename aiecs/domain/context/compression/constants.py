# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Compression kernel constants — ported from OpenHarness compact/__init__.py."""

from __future__ import annotations

COMPACTABLE_TOOLS: frozenset[str] = frozenset(
    {
        "read_file",
        "bash",
        "grep",
        "glob",
        "web_search",
        "web_fetch",
        "edit_file",
        "write_file",
    }
)

TIME_BASED_MC_CLEARED_MESSAGE = "[Old tool result content cleared]"

AUTOCOMPACT_BUFFER_TOKENS = 13_000
MAX_OUTPUT_TOKENS_FOR_SUMMARY = 20_000
MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3
COMPACT_TIMEOUT_SECONDS = 25
MAX_COMPACT_STREAMING_RETRIES = 2
MAX_PTL_RETRIES = 3

SESSION_MEMORY_KEEP_RECENT = 12
SESSION_MEMORY_MAX_LINES = 48
SESSION_MEMORY_MAX_CHARS = 4_000

CONTEXT_COLLAPSE_TEXT_CHAR_LIMIT = 2_400
CONTEXT_COLLAPSE_HEAD_CHARS = 900
CONTEXT_COLLAPSE_TAIL_CHARS = 500

MAX_COMPACT_ATTACHMENTS = 6
MAX_DISCOVERED_TOOLS = 12

DEFAULT_KEEP_RECENT = 5
DEFAULT_GAP_THRESHOLD_MINUTES = 60

# W11 tool output thresholds (OpenHarness tool_outputs.py / Claude toolLimits.ts)
DEFAULT_TOOL_OUTPUT_INLINE_CHARS = 16_000  # A9: offload when output exceeds this
DEFAULT_TOOL_OUTPUT_PREVIEW_CHARS = 3_000  # A9: inline preview head after offload
DEFAULT_TOOL_RESULTS_PER_MESSAGE_CHARS = 200_000  # A8: aggregate budget per tool batch
TOOL_OUTPUT_TRUNCATED_HEADER = "[Tool output truncated]"
PERSISTED_OUTPUT_TAG = "<persisted-output>"

TOKEN_ESTIMATION_PADDING = 4 / 3
DEFAULT_VISION_IMAGE_TOKEN_ESTIMATE = 3_072
DEFAULT_CONTEXT_WINDOW = 200_000

PTL_RETRY_MARKER = "[earlier conversation truncated for compaction retry]"
ERROR_MESSAGE_INCOMPLETE_RESPONSE = "Compaction interrupted before a complete summary was returned."
