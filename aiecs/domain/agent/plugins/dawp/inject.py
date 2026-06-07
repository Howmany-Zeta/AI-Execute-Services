# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
inject — merge_back helpers for DAWP runs (§6.3, D1-12).

Two strategies (§6.3):
- ``append`` (default, D2): DAWP prompt chain appends assistant/tool messages directly
  to the main ``messages`` list (passed by reference).  The main loop sees the full
  DAWP history after the run.
- ``inject_only``: DAWP operates on a **copy** of the main messages list so that
  sub-loop detail is not visible to the main loop.  After completion a single
  summary assistant message is appended to the main list (token-efficient).

Usage in ``_drain_pending_dawp_runs``::

    dawp_msgs = messages_for_dawp_run(messages, merge_back=run.merge_back)
    async for event in run_prompt_chain(workflow, dawp_msgs, ...):
        yield event
    if run.merge_back == "inject_only":
        apply_inject_only(messages, workflow_id=run.workflow_id)
    # For "append", dawp_msgs IS messages — already merged in-place; nothing to do.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from aiecs.llm import LLMMessage

# Template for the inject_only summary message (§6.3).
_INJECT_ONLY_SUMMARY = "[DAWP {workflow_id}: run complete]"


def messages_for_dawp_run(
    main_messages: list[LLMMessage],
    *,
    merge_back: Literal["append", "inject_only"],
) -> list[LLMMessage]:
    """Return the message list to pass to ``run_prompt_chain``.

    ``append``
        Returns *main_messages* **by reference**.  Any messages that the DAWP prompt
        chain appends are immediately visible in the main conversation list.

    ``inject_only``
        Returns a **shallow copy** of *main_messages*.  The DAWP prompt chain writes
        into the copy; the main list is unaffected.  Call :func:`apply_inject_only`
        after the run to add the summary.

    Args:
        main_messages: The current main-loop conversation history.
        merge_back: Merge strategy declared in the workflow activation (§6.3).

    Returns:
        The message list to pass to the DAWP prompt chain runner.
    """
    if merge_back == "inject_only":
        return list(main_messages)
    return main_messages  # "append" — share reference, DAWP appends in-place


def apply_inject_only(
    main_messages: list[LLMMessage],
    *,
    workflow_id: str,
) -> None:
    """Append a single run-complete summary assistant message (``inject_only`` mode).

    Must be called **after** ``run_prompt_chain`` returns when
    ``merge_back="inject_only"``.  For ``append`` mode this function must NOT be
    called — the in-place mutation by the DAWP runner already handled merge_back.

    Args:
        main_messages: The main-loop conversation history to mutate in-place.
        workflow_id:   Workflow identifier included in the summary text.
    """
    from aiecs.llm import LLMMessage

    summary = _INJECT_ONLY_SUMMARY.format(workflow_id=workflow_id)
    main_messages.append(LLMMessage(role="assistant", content=summary))
