"""
Unit tests for D1-11 — DawpPlugin.on_build_messages trigger_instruction injection (§9).

Scenarios:
- on_response_trigger activation with trigger_instruction → system message appended
- on_response_trigger activation without trigger_instruction → no injection
- pre_main_loop activation (with or without trigger_instruction) → no injection
- multiple on_response_trigger activations → one system message per activation
- empty plugin_state (no scheduler key) → messages unchanged
- empty workflow_activations list → messages unchanged
- fixture: trigger_inline.dawp.md trigger_instruction content injected correctly
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from aiecs.domain.agent.plugins.builtin.dawp_plugin import (
    PLUGIN_STATE_SCHEDULER_KEY,
    DawpPlugin,
)
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.dawp.schema import (
    Activation,
    OnResponseTriggerPlacement,
    PreMainLoopPlacement,
)
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.llm import LLMMessage

_FIXTURE_PATH = str(
    Path(__file__).parents[4] / "fixtures" / "dawp" / "trigger_inline.dawp.md"
)

_TRIGGER = "<START_INLINE_REVIEW>"
_TRIGGER_INSTRUCTION = "When ready, output on its own line:\n<START_INLINE_REVIEW>"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plugin() -> DawpPlugin:
    config = PluginConfig(name="dawp", enabled=True)
    agent = MagicMock()
    return DawpPlugin(config=config, agent=agent)


def _make_ctx(workflow_activations: list | None = None) -> AgentPluginContext:
    ctx = MagicMock(spec=AgentPluginContext)
    ctx.plugin_state = {}
    if workflow_activations is not None:
        ctx.plugin_state[PLUGIN_STATE_SCHEDULER_KEY] = workflow_activations
    return ctx


def _on_response_activation(trigger_instruction: str | None = _TRIGGER_INSTRUCTION) -> Activation:
    return Activation(
        placement=OnResponseTriggerPlacement(dawp_trigger=_TRIGGER),
        trigger_instruction=trigger_instruction,
    )


def _pre_main_loop_activation(trigger_instruction: str | None = None) -> Activation:
    return Activation(
        placement=PreMainLoopPlacement(),
        trigger_instruction=trigger_instruction,
    )


def _system_msgs(messages: list[LLMMessage]) -> list[LLMMessage]:
    return [m for m in messages if m.role == "system"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestOnBuildMessages:
    async def test_on_response_trigger_with_instruction_appends_system_message(self) -> None:
        """on_response_trigger + trigger_instruction → one system message appended."""
        plugin = _make_plugin()
        ctx = _make_ctx([("wf-1", _on_response_activation())])
        base_messages: list[LLMMessage] = []

        result = await plugin.on_build_messages(ctx, base_messages)

        sys_msgs = _system_msgs(result)
        assert len(sys_msgs) == 1
        assert sys_msgs[0].role == "system"
        assert "on its own line" in sys_msgs[0].content

    async def test_trigger_instruction_content_is_stripped(self) -> None:
        """Leading/trailing whitespace in trigger_instruction is stripped."""
        activation = Activation(
            placement=OnResponseTriggerPlacement(dawp_trigger=_TRIGGER),
            trigger_instruction="  Use the trigger.  \n",
        )
        plugin = _make_plugin()
        ctx = _make_ctx([("wf-1", activation)])

        result = await plugin.on_build_messages(ctx, [])

        sys_msgs = _system_msgs(result)
        assert len(sys_msgs) == 1
        assert sys_msgs[0].content == "Use the trigger."

    async def test_on_response_trigger_without_instruction_no_injection(self) -> None:
        """on_response_trigger with trigger_instruction=None → no injection."""
        plugin = _make_plugin()
        ctx = _make_ctx([("wf-1", _on_response_activation(trigger_instruction=None))])

        result = await plugin.on_build_messages(ctx, [])

        assert _system_msgs(result) == []

    async def test_on_response_trigger_empty_instruction_no_injection(self) -> None:
        """on_response_trigger with trigger_instruction='' → no injection (falsy)."""
        activation = Activation(
            placement=OnResponseTriggerPlacement(dawp_trigger=_TRIGGER),
            trigger_instruction="",
        )
        plugin = _make_plugin()
        ctx = _make_ctx([("wf-1", activation)])

        result = await plugin.on_build_messages(ctx, [])

        assert _system_msgs(result) == []

    async def test_pre_main_loop_activation_not_injected(self) -> None:
        """pre_main_loop activations are never injected into build_messages."""
        plugin = _make_plugin()
        ctx = _make_ctx([("wf-1", _pre_main_loop_activation(trigger_instruction="hint"))])

        result = await plugin.on_build_messages(ctx, [])

        assert result == []

    async def test_pre_main_loop_with_trigger_instruction_not_injected(self) -> None:
        """pre_main_loop with trigger_instruction set → still not injected."""
        plugin = _make_plugin()
        ctx = _make_ctx([
            ("wf-1", _pre_main_loop_activation(trigger_instruction="do something"))
        ])

        result = await plugin.on_build_messages(ctx, [])

        assert _system_msgs(result) == []

    async def test_multiple_on_response_trigger_each_injected(self) -> None:
        """Two on_response_trigger activations → two system messages appended."""
        a1 = Activation(
            placement=OnResponseTriggerPlacement(dawp_trigger="<TRIGGER_ONE>"),
            trigger_instruction="hint one",
        )
        a2 = Activation(
            placement=OnResponseTriggerPlacement(dawp_trigger="<TRIGGER_TWO>"),
            trigger_instruction="hint two",
        )
        plugin = _make_plugin()
        ctx = _make_ctx([("wf-a", a1), ("wf-b", a2)])

        result = await plugin.on_build_messages(ctx, [])

        sys_msgs = _system_msgs(result)
        assert len(sys_msgs) == 2
        contents = {m.content for m in sys_msgs}
        assert "hint one" in contents
        assert "hint two" in contents

    async def test_mixed_activations_only_on_response_trigger_injected(self) -> None:
        """Mixed activations: only on_response_trigger with instruction is injected."""
        activations = [
            ("wf-pre", _pre_main_loop_activation()),
            ("wf-1", _on_response_activation()),
            ("wf-2", _on_response_activation(trigger_instruction=None)),
        ]
        plugin = _make_plugin()
        ctx = _make_ctx(activations)

        result = await plugin.on_build_messages(ctx, [])

        sys_msgs = _system_msgs(result)
        assert len(sys_msgs) == 1

    async def test_existing_messages_preserved(self) -> None:
        """Pre-existing messages in the list are not removed or reordered."""
        plugin = _make_plugin()
        ctx = _make_ctx([("wf-1", _on_response_activation())])
        existing = [
            LLMMessage(role="system", content="Base system prompt."),
            LLMMessage(role="user", content="Hello"),
        ]

        result = await plugin.on_build_messages(ctx, existing)

        # Existing messages are first
        assert result[0].content == "Base system prompt."
        assert result[1].role == "user"
        # New system message is appended at end
        sys_msgs = _system_msgs(result)
        assert sys_msgs[-1].content == _TRIGGER_INSTRUCTION

    async def test_empty_plugin_state_no_scheduler_key_returns_messages_unchanged(self) -> None:
        """Plugin state without PLUGIN_STATE_SCHEDULER_KEY → no modification."""
        plugin = _make_plugin()
        ctx = _make_ctx(None)  # no scheduler key in plugin_state
        original = [LLMMessage(role="system", content="Existing.")]

        result = await plugin.on_build_messages(ctx, original)

        assert result == original

    async def test_empty_workflow_activations_list_returns_messages_unchanged(self) -> None:
        """Empty workflow_activations list → no injection."""
        plugin = _make_plugin()
        ctx = _make_ctx([])
        original = [LLMMessage(role="system", content="Existing.")]

        result = await plugin.on_build_messages(ctx, original)

        assert result == original

    async def test_returns_new_list_not_mutates_input(self) -> None:
        """on_build_messages must not mutate the input messages list."""
        plugin = _make_plugin()
        ctx = _make_ctx([("wf-1", _on_response_activation())])
        original: list[LLMMessage] = []
        original_id = id(original)

        result = await plugin.on_build_messages(ctx, original)

        assert id(result) != original_id  # new list returned
        assert original == []  # input unchanged


# ---------------------------------------------------------------------------
# Fixture integration: trigger_inline.dawp.md
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestBuildMessagesWithFixture:
    async def _load_scheduler_state(self) -> list:
        """Load the trigger_inline fixture via document_loader and build scheduler list."""
        from aiecs.domain.agent.plugins.dawp import document_loader

        wf = document_loader.compile_file(Path(_FIXTURE_PATH))
        return [(wf.metadata.name, activation) for activation in wf.activations]

    async def test_fixture_trigger_instruction_injected(self) -> None:
        """trigger_inline.dawp.md trigger_instruction is injected as a system message."""
        plugin = _make_plugin()
        ctx = _make_ctx(await self._load_scheduler_state())

        result = await plugin.on_build_messages(ctx, [])

        sys_msgs = _system_msgs(result)
        assert len(sys_msgs) == 1
        assert "<START_INLINE_REVIEW>" in sys_msgs[0].content
        assert "analysis phase is complete" in sys_msgs[0].content

    async def test_fixture_injection_message_is_system_role(self) -> None:
        """Injected message role is 'system'."""
        plugin = _make_plugin()
        ctx = _make_ctx(await self._load_scheduler_state())

        result = await plugin.on_build_messages(ctx, [])

        assert all(m.role == "system" for m in _system_msgs(result))
