# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Agent hook event names (§4.2)."""

from __future__ import annotations

from enum import Enum


class AgentHookEvent(str, Enum):
    """Canonical hook events for HookPlugin v1."""

    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    PRE_COMPACT = "pre_compact"
    POST_COMPACT = "post_compact"
    USER_PROMPT_SUBMIT = "user_prompt_submit"
    STOP = "stop"
    NOTIFICATION = "notification"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    SUBAGENT_STOP = "subagent_stop"  # deprecated alias; loader maps to DAWP_RUN_END (§4.3)
    PRE_MAIN_LOOP = "pre_main_loop"
    POST_TASK = "post_task"
    BUILD_MESSAGES = "build_messages"
    ITERATION_START = "iteration_start"
    ITERATION_END = "iteration_end"
    DAWP_RUN_START = "dawp_run_start"
    DAWP_RUN_END = "dawp_run_end"
    MAX_ITERATIONS = "max_iterations"
    PROMPT_TOO_LONG = "prompt_too_long"
    TOOL_OUTPUT_OFFLOAD = "tool_output_offload"
    LLM_ERROR = "llm_error"
    PERMISSION_REQUEST = "permission_request"
    PERMISSION_DENIED = "permission_denied"
    POST_TOOL_USE_FAILURE = "post_tool_use_failure"
    USER_PROMPT_IN_HISTORY = "user_prompt_in_history"
    SUBAGENT_START = "subagent_start"
    STOP_FAILURE = "stop_failure"
    TASK_COMPLETED = "task_completed"

    @classmethod
    def executable_in_hooks_json(cls) -> frozenset[AgentHookEvent]:
        """Events that may be registered from hooks.json in v1 (§5.3)."""
        return frozenset(
            {
                cls.PRE_TOOL_USE,
                cls.POST_TOOL_USE,
                cls.PRE_COMPACT,
                cls.POST_COMPACT,
                cls.USER_PROMPT_SUBMIT,
                cls.STOP,
                cls.SESSION_START,
                cls.SESSION_END,
                cls.SUBAGENT_STOP,
                cls.PRE_MAIN_LOOP,
                cls.POST_TASK,
                cls.BUILD_MESSAGES,
                cls.ITERATION_START,
                cls.ITERATION_END,
                cls.DAWP_RUN_START,
                cls.DAWP_RUN_END,
                cls.MAX_ITERATIONS,
                cls.PROMPT_TOO_LONG,
                cls.TOOL_OUTPUT_OFFLOAD,
                cls.LLM_ERROR,
                cls.PERMISSION_REQUEST,
                cls.PERMISSION_DENIED,
                cls.POST_TOOL_USE_FAILURE,
                cls.NOTIFICATION,
                cls.USER_PROMPT_IN_HISTORY,
                cls.SUBAGENT_START,
                cls.STOP_FAILURE,
                cls.TASK_COMPLETED,
            }
        )
