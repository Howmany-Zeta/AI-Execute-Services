# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
StepHandler registry for DAWP step completion (§7.2, D3-03).

Default ``*.dawp.md`` steps compile to ``completion.type=marker`` and use
:func:`~completion.prompt_step_complete`.  Legacy / programmatic completion types
(``no_tool_calls``, etc.) register here without changing marker default behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from aiecs.domain.agent.plugins.dawp.completion import prompt_step_complete
from aiecs.domain.agent.plugins.dawp.schema import MarkerCompletion, NoToolCallsCompletion

StepCompletionResult = Literal["prompt_done", "dawp_done", "continue"]

StepHandlerFn = Callable[["StepIterationContext"], StepCompletionResult]


@dataclass(frozen=True)
class StepIterationContext:
    """Inputs for one nested-runner iteration completion check."""

    assistant_text: str
    is_last: bool
    had_tool_calls: bool
    result_success: bool
    completion: MarkerCompletion | NoToolCallsCompletion


class StepHandlerRegistry:
    """Registry mapping ``completion.type`` → handler callable."""

    def __init__(self) -> None:
        self._handlers: dict[str, StepHandlerFn] = {}

    def register(self, completion_type: str, handler: StepHandlerFn) -> None:
        self._handlers[completion_type] = handler

    def get(self, completion_type: str) -> StepHandlerFn | None:
        return self._handlers.get(completion_type)

    def evaluate(self, ctx: StepIterationContext) -> StepCompletionResult:
        handler = self._handlers.get(ctx.completion.type)
        if handler is None:
            handler = self._handlers["marker"]
        return handler(ctx)


def _marker_handler(ctx: StepIterationContext) -> StepCompletionResult:
    if not isinstance(ctx.completion, MarkerCompletion):
        return "continue"
    if not ctx.result_success:
        return "continue"
    return prompt_step_complete(
        ctx.assistant_text,
        prompt_marker=ctx.completion.prompt_marker,
        dawp_marker=ctx.completion.dawp_marker,
        is_last=ctx.completion.is_last,
    )


def _no_tool_calls_handler(ctx: StepIterationContext) -> StepCompletionResult:
    """Complete step when iteration succeeds without tool calls (§7.2)."""
    if not ctx.result_success or ctx.had_tool_calls:
        return "continue"
    if ctx.is_last:
        return "dawp_done"
    return "prompt_done"


def build_default_step_handler_registry() -> StepHandlerRegistry:
    registry = StepHandlerRegistry()
    registry.register("marker", _marker_handler)
    registry.register("no_tool_calls", _no_tool_calls_handler)
    return registry


_default_registry = build_default_step_handler_registry()


def get_step_handler_registry() -> StepHandlerRegistry:
    return _default_registry


def evaluate_step_completion(
    ctx: StepIterationContext,
    *,
    registry: StepHandlerRegistry | None = None,
) -> StepCompletionResult:
    """Dispatch step completion evaluation via registry (default: marker)."""
    return (registry or _default_registry).evaluate(ctx)


def reset_step_handler_registry_for_tests() -> None:
    """Replace global registry with a fresh default (unit tests only)."""
    global _default_registry
    _default_registry = build_default_step_handler_registry()
