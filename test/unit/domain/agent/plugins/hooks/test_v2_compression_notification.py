"""
V2.0 tasks 1.2-1.6: notification hooks, F1/F2 compression, H3 payload enrichment.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
from aiecs.domain.agent.plugins.hooks.loader import HookLoadOptions, load_hooks_from_json, normalize_event_key
from aiecs.domain.agent.plugins.hooks.notifications import dispatch_host_notification
from aiecs.domain.agent.plugins.hooks.registry import AgentHookRegistry
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.domain.agent.plugins.testing.parity import (
    capture_parity_case,
    compare_parity_expect,
    load_parity_fixture,
)
from aiecs.domain.agent.tool_loop_core import ToolLoopCompressionContext, maybe_compact_before_llm
from aiecs.domain.context.compression.metadata import LAYER_L2, LAYER_L3
from aiecs.domain.context.compression.policy import CompressionPolicy
from aiecs.domain.context.compression.state import AutoCompactState
from aiecs.domain.context.compression.types import PreCompactContext
from aiecs.host.compression.transcript_compact import compact_formatted_transcript
from aiecs.llm import LLMMessage

_FIXTURES = Path(__file__).resolve().parents[6] / "tests" / "fixtures" / "plugin_parity"


@pytest.fixture
def plugin_ctx(mock_agent) -> AgentPluginContext:
    return AgentPluginContext(
        agent=mock_agent,
        task={"task_id": "t-v2"},
        context={},
        task_description="v2 compression test",
    )


@pytest.mark.unit
class TestV2NotificationHooks:
    def test_notification_registers_when_v2_enabled(self) -> None:
        registry = AgentHookRegistry()
        load_hooks_from_json(
            {"hooks": {"notification": [{"type": "http", "url": "https://example.com/n"}]}},
            registry,
            options=HookLoadOptions(enable_v2_hooks=True),
        )
        assert len(registry.get_hooks(AgentHookEvent.NOTIFICATION)) == 1

    def test_notification_still_warns_in_v1_mode(self) -> None:
        event = normalize_event_key("Notification", options=HookLoadOptions(enable_v2_hooks=False))
        assert event is None

    @pytest.mark.asyncio
    async def test_registry_notification_before_host_callback(self, plugin_ctx, mock_agent) -> None:
        from aiecs.domain.agent.plugins.builtin.hook_plugin import HookPlugin

        plugin = HookPlugin(
            PluginConfig(
                name="hook",
                enabled=True,
                options={
                    "enable_v2_hooks": True,
                    "inline_hooks": {
                        "notification": [
                            {"type": "http", "url": "https://example.com/n"},
                        ]
                    },
                },
            ),
            mock_agent,
        )
        await plugin.on_agent_init(plugin_ctx)
        plugin_ctx.agent._plugin_manager = type(
            "PM",
            (),
            {"get_plugin": lambda _self, name: plugin if name == "hook" else None},
        )()

        order: list[str] = []

        async def track_callback(_payload: dict) -> None:
            order.append("host")

        plugin_ctx.context["hook_notification_callback"] = track_callback

        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            AsyncMock(side_effect=lambda *_a, **_k: order.append("registry") or MagicMock()),
        ):
            await dispatch_host_notification(
                plugin_ctx,
                tool_name="write_file",
                tool_input={"path": "/tmp/x"},
                reason="confirm",
            )

        assert order == ["registry", "host"]

    @pytest.mark.asyncio
    async def test_host_callback_when_no_registry_entry(self, plugin_ctx) -> None:
        invoked: list[str] = []

        async def track_callback(payload: dict) -> None:
            invoked.append(payload["notification_type"])

        plugin_ctx.context["hook_notification_callback"] = track_callback

        result = await dispatch_host_notification(
            plugin_ctx,
            tool_name="read_file",
            tool_input={},
            reason="info",
        )

        assert result is True
        assert invoked == ["permission_prompt"]


@pytest.mark.unit
class TestF1FormattedTranscript:
    @pytest.mark.asyncio
    async def test_llm_only_chain_no_microcompact(self) -> None:
        transcript = [{"role": "user", "content": "hello " * 200}] * 5
        microcompact_spy = MagicMock(return_value=([], 0))

        with patch(
            "aiecs.host.compression.transcript_compact.auto_compact_if_needed",
            AsyncMock(return_value=([LLMMessage(role="user", content="summary")], True)),
        ) as compact_spy:
            with patch(
                "aiecs.domain.context.compression.orchestrator.microcompact_messages",
                microcompact_spy,
            ):
                rows, did = await compact_formatted_transcript(
                    transcript,
                    llm_client=AsyncMock(),
                    force=True,
                )

        assert did is True
        assert rows[0]["role"] == "user"
        assert "content" in rows[0]
        kwargs = compact_spy.await_args.kwargs
        assert kwargs["policy"].chain == ("llm",)
        assert kwargs["compact_metadata"]["layer"] == LAYER_L2
        assert kwargs["compact_metadata"]["formatted_transcript"] is True
        microcompact_spy.assert_not_called()


@pytest.mark.unit
class TestF2LayerMetadata:
    @pytest.mark.asyncio
    async def test_l3_maybe_compact_populates_layer(self, mock_agent) -> None:
        from aiecs.domain.agent.plugins.builtin.hook_plugin import HookPlugin

        hook = HookPlugin(
            PluginConfig(name="hook", enabled=True, options={"enable_v2_hooks": True}),
            mock_agent,
        )
        ctx = AgentPluginContext(agent=mock_agent, task={}, context={}, task_description="t")
        await hook.on_agent_init(ctx)

        captured: dict = {}

        async def fake_auto_compact(messages, **kwargs):
            captured.update(kwargs.get("compact_metadata") or {})
            return messages, False

        compression_ctx = ToolLoopCompressionContext(
            enabled=True,
            policy=CompressionPolicy(auto_compact_threshold_tokens=10, chain=("llm",)),
            llm_client=AsyncMock(),
            auto_compact_state=AutoCompactState(),
            session_id="sess-1",
        )
        messages = [LLMMessage(role="user", content="word " * 50)] * 4

        with (
            patch.object(ctx, "get_plugin", return_value=hook),
            patch(
                "aiecs.domain.agent.tool_loop_core.auto_compact_if_needed",
                side_effect=fake_auto_compact,
            ),
        ):
            await maybe_compact_before_llm(messages, compression_ctx=compression_ctx, plugin_ctx=ctx)

        assert captured.get("layer") == LAYER_L3
        assert captured.get("session_id") == "sess-1"
        assert captured.get("formatted_transcript") is False

    @pytest.mark.asyncio
    async def test_h3_payload_includes_layer_l3(self, mock_agent) -> None:
        from aiecs.domain.agent.plugins.builtin.hook_plugin import HookPlugin
        from aiecs.domain.agent.plugins.hooks.bridge_compression import BridgedCompactHookExecutor

        hook = HookPlugin(
            PluginConfig(
                name="hook",
                enabled=True,
                options={
                    "enable_v2_hooks": True,
                    "inline_hooks": {
                        "pre_compact": [{"type": "http", "url": "https://example.com/pre"}],
                    },
                },
            ),
            mock_agent,
        )
        ctx = AgentPluginContext(agent=mock_agent, task={}, context={}, task_description="t")
        await hook.on_agent_init(ctx)

        bridged = BridgedCompactHookExecutor(None, ctx)
        payloads: list[dict] = []

        async def capture_dispatch(_ctx, event, payload, *, nested=False):
            payloads.append(dict(payload))
            return MagicMock(blocked=False, modified_output=None, results=[])

        pre_ctx = PreCompactContext(
            messages=[LLMMessage(role="user", content="hi")],
            trigger="auto",
            metadata={
                "layer": LAYER_L3,
                "session_id": "s1",
                "formatted_transcript": False,
                "estimated_tokens": 42,
            },
        )

        with (
            patch.object(ctx, "get_plugin", return_value=hook),
            patch(
                "aiecs.domain.agent.plugins.hooks.bridge_compression.dispatch_agent_hook",
                side_effect=capture_dispatch,
            ),
        ):
            await bridged.execute_pre_compact(pre_ctx)

        assert payloads
        assert payloads[0]["layer"] == LAYER_L3
        assert payloads[0]["estimated_tokens"] == 42


@pytest.mark.unit
class TestV2ParityFixture:
    @pytest.mark.asyncio
    async def test_hook_v2_baseline_parity_fixture(self) -> None:
        case = load_parity_fixture(_FIXTURES / "hook_v2_baseline.yaml")
        got = await capture_parity_case(case)
        mismatches = compare_parity_expect(case.expect, got)
        assert mismatches == [], f"mismatch in {mismatches}"
