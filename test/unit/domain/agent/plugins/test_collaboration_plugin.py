"""
Unit tests for CollaborationPlugin (E-08, §4.3).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from aiecs.domain.agent.base_agent import BaseAIAgent
from aiecs.domain.agent.models import AgentConfiguration, AgentType
from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.builtin.collaboration_plugin import (
    PLUGIN_STATE_PEERS_KEY,
    CollaborationPlugin,
    format_collaboration_system_hint,
    resolve_collaboration_peers,
)
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.defaults import derive_default_plugins
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.domain.agent.plugins.registry import PluginRegistry
from aiecs.llm import LLMMessage


class PeerStub:
    def __init__(self, name: str, capabilities: list[str] | None = None) -> None:
        self.name = name
        self.capabilities = capabilities or []


class CollaborationTestAgent(BaseAIAgent):
    """Minimal agent with collaboration fields for plugin tests."""

    def __init__(
        self,
        *,
        collaboration_enabled: bool = False,
        agent_registry: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._collaboration_enabled = collaboration_enabled
        self._agent_registry = agent_registry or {}

    async def _initialize(self) -> None:
        pass

    async def _shutdown(self) -> None:
        pass

    async def execute_task(self, task: dict, context: dict) -> dict:
        return {"success": True, "output": "ok"}

    async def process_message(self, message: str, sender_id: str | None = None) -> dict:
        return {"response": "ok"}


def _make_ctx(agent: BaseAIAgent) -> AgentPluginContext:
    return AgentPluginContext(
        agent=agent,
        task={"description": "Collaboration test task"},
        context={},
        task_description="Collaboration test task",
    )


def _collaboration_plugin(agent: BaseAIAgent, **options: Any) -> CollaborationPlugin:
    return CollaborationPlugin(
        PluginConfig(name="collaboration", enabled=True, options=dict(options)),
        agent,
    )


@pytest.fixture
def collaboration_agent() -> CollaborationTestAgent:
    return CollaborationTestAgent(
        agent_id="agent-1",
        name="Primary Agent",
        agent_type=AgentType.CONVERSATIONAL,
        config=AgentConfiguration(goal="Collaboration plugin test"),
        tools=[],
        collaboration_enabled=True,
        agent_registry={
            "agent-2": PeerStub("Research Assistant", ["search", "summarize"]),
            "agent-3": PeerStub("Data Analyst", ["statistics"]),
        },
    )


@pytest.mark.unit
class TestResolveCollaborationPeers:
    def test_peers_from_agent_registry(self, collaboration_agent: CollaborationTestAgent) -> None:
        peers = resolve_collaboration_peers(collaboration_agent, {})
        assert peers == [
            {
                "agent_id": "agent-2",
                "name": "Research Assistant",
                "capabilities": ["search", "summarize"],
            },
            {
                "agent_id": "agent-3",
                "name": "Data Analyst",
                "capabilities": ["statistics"],
            },
        ]

    def test_peers_from_config_options(self, collaboration_agent: CollaborationTestAgent) -> None:
        peers = resolve_collaboration_peers(
            collaboration_agent,
            {
                "peers": [
                    {"agent_id": "custom-1", "name": "Custom Peer", "capabilities": ["review"]},
                ],
            },
        )
        assert peers == [
            {"agent_id": "custom-1", "name": "Custom Peer", "capabilities": ["review"]},
        ]

    def test_excludes_self_from_registry(self, collaboration_agent: CollaborationTestAgent) -> None:
        collaboration_agent._agent_registry["agent-1"] = PeerStub("Primary Agent")
        peers = resolve_collaboration_peers(collaboration_agent, {})
        assert [peer["agent_id"] for peer in peers] == ["agent-2", "agent-3"]


@pytest.mark.unit
class TestCollaborationPluginInit:
    @pytest.mark.asyncio
    async def test_on_agent_init_sets_plugin_state_peers(
        self,
        collaboration_agent: CollaborationTestAgent,
    ) -> None:
        plugin = _collaboration_plugin(collaboration_agent)
        ctx = _make_ctx(collaboration_agent)

        await plugin.on_agent_init(ctx)

        assert PLUGIN_STATE_PEERS_KEY in ctx.plugin_state
        peers = ctx.plugin_state[PLUGIN_STATE_PEERS_KEY]
        assert isinstance(peers, list)
        assert len(peers) == 2
        assert peers[0]["agent_id"] == "agent-2"

    @pytest.mark.asyncio
    async def test_on_agent_init_empty_when_collaboration_disabled(
        self,
        collaboration_agent: CollaborationTestAgent,
    ) -> None:
        collaboration_agent._collaboration_enabled = False
        plugin = _collaboration_plugin(collaboration_agent)
        ctx = _make_ctx(collaboration_agent)

        await plugin.on_agent_init(ctx)

        assert ctx.plugin_state.get(PLUGIN_STATE_PEERS_KEY) is None
        assert plugin._peers == []

    @pytest.mark.asyncio
    async def test_plugin_manager_init_populates_peers(
        self,
        collaboration_agent: CollaborationTestAgent,
    ) -> None:
        from aiecs.domain.agent.plugins.manager import PluginManager

        configs = [
            PluginConfig(name="collaboration", enabled=True, options={"inject_system_hint": True}),
        ]
        manager = PluginManager(
            agent=collaboration_agent,
            plugin_configs=configs,
            registry=PluginRegistry.default(),
        )
        init_ctx = AgentPluginContext(
            agent=collaboration_agent,
            task={},
            context={},
            task_description="",
        )

        await manager.initialize()

        plugin = manager._plugins["collaboration"]
        assert isinstance(plugin, CollaborationPlugin)
        assert len(plugin._peers) == 2

        await plugin.on_agent_init(init_ctx)
        assert len(init_ctx.plugin_state[PLUGIN_STATE_PEERS_KEY]) == 2


@pytest.mark.unit
class TestCollaborationPluginBuildMessages:
    @pytest.mark.asyncio
    async def test_build_messages_adds_system_hint_when_enabled(
        self,
        collaboration_agent: CollaborationTestAgent,
    ) -> None:
        plugin = _collaboration_plugin(collaboration_agent)
        ctx = _make_ctx(collaboration_agent)
        await plugin.on_agent_init(ctx)

        messages = [
            LLMMessage(role="system", content="Base system prompt"),
            LLMMessage(role="user", content="Task: test"),
        ]
        updated = await plugin.on_build_messages(ctx, messages)

        assert len(updated) == 3
        assert updated[-1].role == "system"
        assert "Available collaborating agents:" in updated[-1].content
        assert "agent-2: Research Assistant" in updated[-1].content

    @pytest.mark.asyncio
    async def test_build_messages_skips_hint_when_inject_disabled(
        self,
        collaboration_agent: CollaborationTestAgent,
    ) -> None:
        plugin = _collaboration_plugin(collaboration_agent, inject_system_hint=False)
        ctx = _make_ctx(collaboration_agent)
        await plugin.on_agent_init(ctx)

        messages = [LLMMessage(role="user", content="Task: test")]
        updated = await plugin.on_build_messages(ctx, messages)

        assert updated == messages

    @pytest.mark.asyncio
    async def test_build_messages_skips_hint_when_no_peers(
        self,
        collaboration_agent: CollaborationTestAgent,
    ) -> None:
        collaboration_agent._agent_registry = {}
        plugin = _collaboration_plugin(collaboration_agent)
        ctx = _make_ctx(collaboration_agent)
        await plugin.on_agent_init(ctx)

        messages = [LLMMessage(role="user", content="Task: test")]
        updated = await plugin.on_build_messages(ctx, messages)

        assert updated == messages


@pytest.mark.unit
class TestCollaborationPluginDerive:
    def test_derive_enables_when_collaboration_enabled(self, mock_agent) -> None:
        mock_agent._collaboration_enabled = True
        by_name = {plugin.name: plugin for plugin in derive_default_plugins(mock_agent._config, mock_agent)}
        assert by_name["collaboration"].enabled is True

    def test_derive_disabled_when_collaboration_disabled(self, mock_agent) -> None:
        mock_agent._collaboration_enabled = False
        by_name = {plugin.name: plugin for plugin in derive_default_plugins(mock_agent._config, mock_agent)}
        assert by_name["collaboration"].enabled is False


@pytest.mark.unit
class TestCollaborationPluginBoundary:
    def test_plugin_has_no_delegate_task_or_rpc(self) -> None:
        assert not hasattr(CollaborationPlugin, "delegate_task")
        assert CollaborationPlugin.on_pre_main_loop is BaseAgentPlugin.on_pre_main_loop

    def test_format_collaboration_system_hint(self) -> None:
        hint = format_collaboration_system_hint(
            [{"agent_id": "a2", "name": "Peer", "capabilities": ["search"]}],
        )
        assert "Available collaborating agents:" in hint
        assert "a2: Peer (capabilities: search)" in hint

    @pytest.mark.asyncio
    async def test_plugin_never_calls_agent_delegate_task(
        self,
        collaboration_agent: CollaborationTestAgent,
    ) -> None:
        collaboration_agent.delegate_task = AsyncMock()
        plugin = _collaboration_plugin(collaboration_agent)
        ctx = _make_ctx(collaboration_agent)

        await plugin.on_agent_init(ctx)
        await plugin.on_build_messages(ctx, [LLMMessage(role="user", content="Task")])

        collaboration_agent.delegate_task.assert_not_called()
