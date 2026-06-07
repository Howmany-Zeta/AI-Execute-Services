# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
suppress: remove ``dawp_start`` tool_call / tool_result pair from LLM message context (D2-03, §4.3.1).

Background
----------
OpenAI / Anthropic APIs require that every assistant ``tool_calls`` entry has a
corresponding ``tool`` role ``tool_result``.  Sending ``tool_calls`` without a
matching result causes a **400 / invalid messages** error.  Therefore suppression
MUST remove **both** messages as an atomic pair — never just the result.

Contract
--------
- The audit record (``state.steps``) is written **before** suppress is called;
  streaming ``tool_result`` events are yielded **before** suppress is called.
  ``apply_suppress_from_llm`` therefore only modifies the LLM-visible message list.
- An assistant message whose ``tool_calls`` list contains only ``dawp_start`` is
  removed entirely.  If it also had other tool calls (D13 violation scenario), the
  whole message is still removed — per §4.3.2 ``dawp_start`` must be the sole call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiecs.llm import LLMMessage


def _is_suppressed_tool_pair(m: "LLMMessage", tool_call_id: str) -> bool:
    """Return ``True`` if *m* is one of the two messages forming the suppressed pair.

    Matches:
    - ``role="tool"`` messages whose ``tool_call_id`` equals *tool_call_id*.
    - ``role="assistant"`` messages whose ``tool_calls`` list contains *tool_call_id*.
    """
    if m.role == "tool":
        return m.tool_call_id == tool_call_id
    if m.role == "assistant" and m.tool_calls:
        return any(tc.get("id") == tool_call_id for tc in m.tool_calls)
    return False


def apply_suppress_from_llm(
    messages: "list[LLMMessage]",
    tool_call_id: str,
) -> "list[LLMMessage]":
    """Return a new message list with the *tool_call_id* pair removed.

    Removes:
    1. The ``role="assistant"`` message whose ``tool_calls`` includes *tool_call_id*.
    2. The ``role="tool"`` message with ``tool_call_id`` matching.

    Leaves all other messages (including system, user, and unrelated tool pairs)
    untouched.  The original list is not mutated.

    CRITICAL: both messages are removed together.  Removing only the ``tool_result``
    while keeping the assistant ``tool_calls`` entry produces a malformed message
    sequence that causes **400 / invalid messages** from LLM providers (§4.3.1).

    Args:
        messages:     Current LLM message history.
        tool_call_id: The ``id`` of the ``dawp_start`` tool call to suppress.

    Returns:
        New list with the paired assistant + tool messages filtered out.
    """
    return [m for m in messages if not _is_suppressed_tool_pair(m, tool_call_id)]
