"""
Unit tests for MemoryPlugin business logic (§7.2, P2-03).
"""

from __future__ import annotations

from typing import Any
import pytest

from aiecs.domain.agent.base_agent import BaseAIAgent
from aiecs.domain.agent.models import AgentConfiguration, AgentType
from aiecs.domain.agent.plugins.builtin.memory_plugin import (
    MemoryPlugin,
    expand_context_history_entries,
)
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.manager import PluginManager
from aiecs.domain.agent.plugins.models import PluginConfig, PluginPhase
from aiecs.domain.agent.plugins.registry import PluginRegistry
from aiecs.domain.agent.plugins.testing.normalize import normalize_messages
from aiecs.llm import LLMMessage


class MemoryTestAgent(BaseAIAgent):
    """BaseAIAgent for MemoryPlugin tests (LLMAgent / ToolAgent stand-in)."""

    async def _initialize(self) -> None:
        pass

    async def _shutdown(self) -> None:
        pass

    async def execute_task(self, task: dict, context: dict) -> dict:
        return {"success": True, "output": "ok"}

    async def process_message(self, message: str, sender_id: str | None = None) -> dict:
        return {"response": "ok"}


class HybridAgent(MemoryTestAgent):
    """In-test HybridAgent stand-in for §7.2 ``context.history`` branch."""


class LLMAgent(MemoryTestAgent):
    """In-test LLMAgent stand-in for §7.2 ``_conversation_history`` branch."""


class ToolAgent(MemoryTestAgent):
    """In-test ToolAgent stand-in for §7.2 ``_conversation_history`` branch."""


@pytest.fixture
def memory_test_agent() -> LLMAgent:
    config = AgentConfiguration(goal="Memory plugin test", memory_enabled=True)
    agent = LLMAgent(
        agent_id="memory-plugin-test",
        name="Memory Plugin Test",
        agent_type=AgentType.CONVERSATIONAL,
        config=config,
        tools=[],
    )
    agent._conversation_history = []
    return agent


@pytest.fixture
def hybrid_memory_test_agent() -> HybridAgent:
    config = AgentConfiguration(goal="Memory plugin test", memory_enabled=True)
    agent = HybridAgent(
        agent_id="memory-plugin-hybrid-test",
        name="Memory Plugin Hybrid Test",
        agent_type=AgentType.DEVELOPER,
        config=config,
        tools=[],
    )
    agent._conversation_history = []
    return agent


def _make_ctx(
    agent: MemoryTestAgent,
    context: dict[str, Any] | None = None,
    task_description: str = "Follow-up question",
) -> AgentPluginContext:
    return AgentPluginContext(
        agent=agent,
        task={"description": task_description},
        context=context or {},
        task_description=task_description,
    )


def _memory_manager(agent: MemoryTestAgent, **options: Any) -> PluginManager:
    registry = PluginRegistry()
    registry.register("memory", MemoryPlugin, origin="registry")
    opts = {
        "capacity": 100,
        "persist": False,
        "session_key": "session_id",
        **options,
    }
    return PluginManager(
        agent,
        [PluginConfig(name="memory", enabled=True, options=opts)],
        registry=registry,
    )


@pytest.mark.unit
class TestExpandContextHistory:
    def test_preserves_roles_and_order(self) -> None:
        history = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"},
            {"role": "user", "content": "What about tomorrow?"},
        ]
        messages = expand_context_history_entries(history)

        assert [m.role for m in messages] == ["user", "assistant", "user"]
        assert [m.content for m in messages] == [
            "Previous question",
            "Previous answer",
            "What about tomorrow?",
        ]

    def test_supports_llmmessage_instances(self) -> None:
        history = [
            LLMMessage(role="user", content="Hello"),
            LLMMessage(role="assistant", content="Hi there!"),
        ]
        messages = expand_context_history_entries(history)
        assert len(messages) == 2
        assert messages[0].content == "Hello"


@pytest.mark.unit
@pytest.mark.asyncio
class TestMemoryPluginBuildMessages:
    async def test_context_history_expanded_after_system_message(
        self, hybrid_memory_test_agent: HybridAgent
    ) -> None:
        manager = _memory_manager(hybrid_memory_test_agent)
        await manager.initialize()

        ctx = _make_ctx(
            hybrid_memory_test_agent,
            context={
                "history": [
                    {"role": "user", "content": "Previous question"},
                    {"role": "assistant", "content": "Previous answer"},
                ],
            },
        )
        initial = [LLMMessage(role="system", content="System prompt")]
        result = await manager.run_phase(
            PluginPhase.BUILD_MESSAGES,
            ctx=ctx,
            messages=initial,
        )

        assert result[0].role == "system"
        assert [m.role for m in result[1:]] == ["user", "assistant"]
        assert result[1].content == "Previous question"
        assert result[2].content == "Previous answer"

    async def test_conversation_memory_branch_when_no_context_history(
        self, memory_test_agent: LLMAgent
    ) -> None:
        manager = _memory_manager(memory_test_agent)
        await manager.initialize()
        plugin = manager.get_plugin("memory")
        assert isinstance(plugin, MemoryPlugin)

        session_id = "sess-llm-branch"
        plugin._memory.create_session(session_id)
        plugin._memory.add_message(session_id, "user", "Stored user")
        plugin._memory.add_message(session_id, "assistant", "Stored assistant")

        ctx = _make_ctx(memory_test_agent, context={"session_id": session_id})
        result = await manager.run_phase(
            PluginPhase.BUILD_MESSAGES,
            ctx=ctx,
            messages=[LLMMessage(role="system", content="sys")],
        )

        roles = [m.role for m in result[1:]]
        assert roles == ["user", "assistant"]
        assert result[1].content == "Stored user"

    async def test_llm_agent_uses_conversation_history_not_context_history(
        self, memory_test_agent: LLMAgent
    ) -> None:
        """§7.2: LLMAgent path prefers ``_conversation_history`` over ``context.history``."""
        memory_test_agent._conversation_history = [
            LLMMessage(role="user", content="Stored user turn"),
            LLMMessage(role="assistant", content="Stored assistant turn"),
        ]
        manager = _memory_manager(memory_test_agent)
        await manager.initialize()

        ctx = _make_ctx(
            memory_test_agent,
            context={
                "history": [
                    {"role": "user", "content": "Context history should be ignored"},
                ],
            },
        )
        result = await manager.run_phase(
            PluginPhase.BUILD_MESSAGES,
            ctx=ctx,
            messages=[LLMMessage(role="system", content="sys")],
        )

        assert [m.content for m in result[1:]] == [
            "Stored user turn",
            "Stored assistant turn",
        ]

    async def test_llm_agent_build_messages_matches_p3_00_multiturn_golden(
        self, memory_test_agent: LLMAgent
    ) -> None:
        """BUILD_MESSAGES + user task matches ``llm_memory_multiturn`` golden (P3-00)."""
        memory_test_agent._conversation_history = [
            LLMMessage(role="user", content="What is artificial intelligence?"),
            LLMMessage(
                role="assistant",
                content="AI is the simulation of human intelligence by machines.",
            ),
        ]
        manager = _memory_manager(memory_test_agent)
        await manager.initialize()

        ctx = _make_ctx(
            memory_test_agent,
            task_description="Follow-up question about AI",
        )
        built = await manager.run_phase(
            PluginPhase.BUILD_MESSAGES,
            ctx=ctx,
            messages=[
                LLMMessage(role="system", content="You are a plugin parity LLM agent."),
            ],
        )
        full_messages = [
            *built,
            LLMMessage(role="user", content="Follow-up question about AI"),
        ]
        normalized = normalize_messages(full_messages)

        assert normalized == [
            {"role": "system", "content": "You are a plugin parity LLM agent."},
            {"role": "user", "content": "What is artificial intelligence?"},
            {
                "role": "assistant",
                "content": "AI is the simulation of human intelligence by machines.",
            },
            {"role": "user", "content": "Follow-up question about AI"},
        ]

    async def test_tool_agent_uses_conversation_history(
        self,
    ) -> None:
        config = AgentConfiguration(goal="Tool memory test", memory_enabled=True)
        agent = ToolAgent(
            agent_id="tool-memory-test",
            name="Tool Memory Test",
            agent_type=AgentType.TASK_EXECUTOR,
            config=config,
            tools=[],
        )
        agent._conversation_history = [
            LLMMessage(role="user", content="Tool user"),
            LLMMessage(role="assistant", content="Tool assistant"),
        ]
        manager = _memory_manager(agent)
        await manager.initialize()

        ctx = _make_ctx(
            agent,
            context={"history": [{"role": "user", "content": "ignored"}]},
        )
        result = await manager.run_phase(
            PluginPhase.BUILD_MESSAGES,
            ctx=ctx,
            messages=[LLMMessage(role="system", content="tool sys")],
        )
        assert [m.content for m in result[1:]] == ["Tool user", "Tool assistant"]


@pytest.mark.unit
@pytest.mark.asyncio
class TestMemoryPluginPreTask:
    async def test_pre_task_does_not_clobber_existing_history(
        self, hybrid_memory_test_agent: HybridAgent
    ) -> None:
        manager = _memory_manager(hybrid_memory_test_agent)
        await manager.initialize()

        original_history = [
            {"role": "user", "content": "Caller history"},
            {"role": "assistant", "content": "Caller reply"},
        ]
        ctx = _make_ctx(
            hybrid_memory_test_agent,
            context={"history": list(original_history), "session_id": "sess-1"},
        )

        await manager.run_phase(PluginPhase.PRE_TASK, ctx=ctx)

        assert ctx.context["history"] == original_history

    async def test_pre_task_loads_history_when_missing(
        self, hybrid_memory_test_agent: HybridAgent
    ) -> None:
        manager = _memory_manager(hybrid_memory_test_agent)
        await manager.initialize()
        plugin = manager.get_plugin("memory")
        assert isinstance(plugin, MemoryPlugin)

        session_id = "sess-load"
        plugin._memory.create_session(session_id)
        plugin._memory.add_message(session_id, "user", "Loaded user")
        plugin._memory.add_message(session_id, "assistant", "Loaded assistant")

        ctx = _make_ctx(hybrid_memory_test_agent, context={"session_id": session_id})
        await manager.run_phase(PluginPhase.PRE_TASK, ctx=ctx)

        assert len(ctx.context["history"]) == 2
        assert ctx.context["history"][0]["role"] == "user"
        assert ctx.context["history"][1]["content"] == "Loaded assistant"

    async def test_pre_task_llm_agent_hydrates_conversation_history(
        self, memory_test_agent: LLMAgent
    ) -> None:
        manager = _memory_manager(memory_test_agent)
        await manager.initialize()
        plugin = manager.get_plugin("memory")
        assert isinstance(plugin, MemoryPlugin)

        session_id = "sess-llm-pre"
        plugin._memory.create_session(session_id)
        plugin._memory.add_message(session_id, "user", "Hydrated user")
        plugin._memory.add_message(session_id, "assistant", "Hydrated assistant")

        ctx = _make_ctx(memory_test_agent, context={"session_id": session_id})
        await manager.run_phase(PluginPhase.PRE_TASK, ctx=ctx)

        assert "history" not in ctx.context
        assert len(memory_test_agent._conversation_history) == 2
        assert memory_test_agent._conversation_history[0].content == "Hydrated user"


@pytest.mark.unit
@pytest.mark.asyncio
class TestMemoryPluginPostTask:
    async def test_post_task_increases_stored_turns(
        self, hybrid_memory_test_agent: HybridAgent
    ) -> None:
        manager = _memory_manager(hybrid_memory_test_agent)
        await manager.initialize()
        plugin = manager.get_plugin("memory")
        assert isinstance(plugin, MemoryPlugin)

        session_id = "sess-post"
        plugin._memory.create_session(session_id)
        ctx = _make_ctx(
            hybrid_memory_test_agent,
            context={"session_id": session_id},
            task_description="New user question",
        )

        before = len(plugin._memory.get_history(session_id))
        await manager.run_phase(
            PluginPhase.POST_TASK,
            ctx=ctx,
            result={"final_response": "New assistant answer"},
        )
        after = len(plugin._memory.get_history(session_id))

        assert after == before + 2
        history = plugin._memory.get_history(session_id)
        assert history[-2].role == "user"
        assert history[-2].content == "New user question"
        assert history[-1].role == "assistant"
        assert history[-1].content == "New assistant answer"

    async def test_post_task_llm_agent_appends_conversation_history(
        self, memory_test_agent: LLMAgent
    ) -> None:
        manager = _memory_manager(memory_test_agent)
        await manager.initialize()

        ctx = _make_ctx(
            memory_test_agent,
            task_description="Second question",
        )
        await manager.run_phase(
            PluginPhase.POST_TASK,
            ctx=ctx,
            result={"output": "Second answer"},
        )

        assert len(memory_test_agent._conversation_history) == 2
        assert memory_test_agent._conversation_history[0].role == "user"
        assert memory_test_agent._conversation_history[0].content == "Second question"
        assert memory_test_agent._conversation_history[1].content == "Second answer"

    async def test_get_history_and_append_turn_helpers(
        self, memory_test_agent: LLMAgent
    ) -> None:
        manager = _memory_manager(memory_test_agent)
        await manager.initialize()
        plugin = manager.get_plugin("memory")
        assert isinstance(plugin, MemoryPlugin)

        await plugin.append_turn("user", "hello", session_id="helper-sess")
        await plugin.append_turn("assistant", "world", session_id="helper-sess")

        history = await plugin.get_history("helper-sess")
        assert len(history) == 2
        assert history[0].content == "hello"


@pytest.mark.unit
@pytest.mark.asyncio
class TestMemoryPluginAgentInit:
    async def test_agent_init_noop_when_memory_disabled(self) -> None:
        config = AgentConfiguration(goal="Disabled memory", memory_enabled=False)
        agent = LLMAgent(
            agent_id="memory-disabled-test",
            name="Memory Disabled",
            agent_type=AgentType.CONVERSATIONAL,
            config=config,
            tools=[],
        )
        agent._conversation_history = []
        registry = PluginRegistry()
        registry.register("memory", MemoryPlugin, origin="registry")
        manager = PluginManager(
            agent,
            [
                PluginConfig(
                    name="memory",
                    enabled=True,
                    options={"capacity": 100, "persist": False},
                )
            ],
            registry=registry,
        )
        await manager.initialize()
        plugin = manager.get_plugin("memory")
        assert isinstance(plugin, MemoryPlugin)
        assert plugin._memory is None

        ctx = _make_ctx(agent)
        result = await manager.run_phase(
            PluginPhase.BUILD_MESSAGES,
            ctx=ctx,
            messages=[LLMMessage(role="system", content="sys")],
        )
        assert result == [LLMMessage(role="system", content="sys")]
