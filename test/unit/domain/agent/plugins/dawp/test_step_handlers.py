"""Tests for DAWP StepHandler registry (D3-03)."""

from __future__ import annotations

import pytest

from aiecs.domain.agent.plugins.dawp.completion import prompt_step_complete
from aiecs.domain.agent.plugins.dawp.schema import MarkerCompletion, NoToolCallsCompletion
from aiecs.domain.agent.plugins.dawp.step_handlers import (
    StepHandlerRegistry,
    StepIterationContext,
    build_default_step_handler_registry,
    evaluate_step_completion,
    reset_step_handler_registry_for_tests,
)


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    reset_step_handler_registry_for_tests()
    yield
    reset_step_handler_registry_for_tests()


def _marker_completion(*, is_last: bool = False) -> MarkerCompletion:
    return MarkerCompletion(
        prompt_marker="<STEP_DONE>",
        dawp_marker="<DAWP_DONE>",
        is_last=is_last,
    )


@pytest.mark.unit
class TestStepHandlerRegistry:
    def test_default_registry_has_marker_and_no_tool_calls(self) -> None:
        registry = build_default_step_handler_registry()
        assert registry.get("marker") is not None
        assert registry.get("no_tool_calls") is not None

    def test_custom_handler_registration(self) -> None:
        registry = StepHandlerRegistry()
        registry.register("manual", lambda _ctx: "continue")
        assert registry.get("manual") is not None

    def test_unknown_type_falls_back_to_marker(self) -> None:
        registry = build_default_step_handler_registry()
        # MarkerCompletion is the fallback path for unknown types
        ctx = StepIterationContext(
            assistant_text="done\n<STEP_DONE>",
            is_last=False,
            had_tool_calls=False,
            result_success=True,
            completion=_marker_completion(is_last=False),
        )
        assert registry.evaluate(ctx) == "prompt_done"


@pytest.mark.unit
class TestMarkerHandlerDefaultPath:
    def test_marker_matches_prompt_step_complete(self) -> None:
        text = "analysis\n<STEP_DONE>"
        ctx = StepIterationContext(
            assistant_text=text,
            is_last=False,
            had_tool_calls=False,
            result_success=True,
            completion=_marker_completion(is_last=False),
        )
        assert evaluate_step_completion(ctx) == prompt_step_complete(
            text,
            prompt_marker="<STEP_DONE>",
            dawp_marker="<DAWP_DONE>",
            is_last=False,
        )

    def test_marker_dawp_done_on_last_step(self) -> None:
        text = "final\n<DAWP_DONE>"
        ctx = StepIterationContext(
            assistant_text=text,
            is_last=True,
            had_tool_calls=False,
            result_success=True,
            completion=_marker_completion(is_last=True),
        )
        assert evaluate_step_completion(ctx) == "dawp_done"

    def test_marker_continue_when_no_marker(self) -> None:
        ctx = StepIterationContext(
            assistant_text="still working",
            is_last=False,
            had_tool_calls=False,
            result_success=True,
            completion=_marker_completion(is_last=False),
        )
        assert evaluate_step_completion(ctx) == "continue"


@pytest.mark.unit
class TestNoToolCallsHandler:
    def test_no_tool_calls_advances_step(self) -> None:
        ctx = StepIterationContext(
            assistant_text="text only",
            is_last=False,
            had_tool_calls=False,
            result_success=True,
            completion=NoToolCallsCompletion(is_last=False),
        )
        assert evaluate_step_completion(ctx) == "prompt_done"

    def test_no_tool_calls_completes_run_on_last_step(self) -> None:
        ctx = StepIterationContext(
            assistant_text="text only",
            is_last=True,
            had_tool_calls=False,
            result_success=True,
            completion=NoToolCallsCompletion(is_last=True),
        )
        assert evaluate_step_completion(ctx) == "dawp_done"

    def test_no_tool_calls_with_tools_continues(self) -> None:
        ctx = StepIterationContext(
            assistant_text="used tools",
            is_last=False,
            had_tool_calls=True,
            result_success=True,
            completion=NoToolCallsCompletion(is_last=False),
        )
        assert evaluate_step_completion(ctx) == "continue"
