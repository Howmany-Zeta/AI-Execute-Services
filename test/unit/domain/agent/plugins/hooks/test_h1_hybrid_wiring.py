"""
Integration tests for HybridAgent H1 tool hook wiring (H1-01, H1-03b).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent import AgentConfiguration, HybridAgent
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult
from aiecs.domain.agent.tool_loop_core import ToolLoopRunState
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse


class _HookSpyLLM(BaseLLMClient):
    def __init__(self) -> None:
        super().__init__(provider_name="openai")
        self.call_count = 0

    async def generate_text(self, messages, **kwargs) -> LLMResponse:
        self.call_count += 1
        if self.call_count == 1:
            resp = LLMResponse(content="calling tool", provider="openai", model="m", tokens_used=1)
            setattr(
                resp,
                "tool_calls",
                [
                    {
                        "id": "call_a",
                        "type": "function",
                        "function": {"name": "mock_tool__query", "arguments": "{}"},
                    }
                ],
            )
            return resp
        return LLMResponse(content="done", provider="openai", model="m", tokens_used=1)

    async def stream_text(self, *args, **kwargs):
        raise NotImplementedError

    async def close(self) -> None:
        return None


@pytest.mark.unit
class TestHybridAgentToolHooks:
    @pytest.mark.asyncio
    async def test_batch_calls_dispatch_tool_with_hooks(self) -> None:
        mock_tool = MagicMock()
        mock_tool.name = "mock_tool"
        mock_tool.run_async = AsyncMock(return_value={"ok": True})

        dispatch_spy = AsyncMock(
            return_value=type(
                "R",
                (),
                {
                    "blocked": False,
                    "error_message": None,
                    "tool_output": {"ok": True},
                    "tool_content": '{"ok": true}',
                    "block_reason": "",
                },
            )()
        )

        with patch("aiecs.tools.get_tool", return_value=mock_tool):
            agent = HybridAgent(
                agent_id="h1-agent",
                name="H1 Agent",
                config=AgentConfiguration(llm_model="m"),
                llm_client=_HookSpyLLM(),
                tools=["mock_tool"],
            )

        plugin_ctx = AgentPluginContext(
            agent=agent,
            task={"description": "test"},
            context={},
            task_description="test",
        )
        messages: list[LLMMessage] = []
        state = ToolLoopRunState()

        with patch(
            "aiecs.domain.agent.plugins.hooks.tool_dispatch.dispatch_tool_with_hooks",
            dispatch_spy,
        ):
            await agent._process_tool_calls_batch(
                thought_raw="thought",
                tool_calls_to_process=[
                    {
                        "id": "call_a",
                        "type": "function",
                        "function": {"name": "mock_tool__query", "arguments": "{}"},
                    }
                ],
                messages=messages,
                iteration=0,
                state=state,
                plugin_ctx=plugin_ctx,
            )

        dispatch_spy.assert_awaited_once()
        kwargs = dispatch_spy.await_args.kwargs
        assert kwargs["batch_index"] == 0
        assert kwargs["assistant_turn_committed"] is True
        assert messages[0].role == "assistant"
        assert messages[1].role == "tool"

    @pytest.mark.asyncio
    async def test_block_appends_error_tool_message_without_execute(self) -> None:
        mock_tool = MagicMock()
        mock_tool.run_async = AsyncMock(return_value={"ok": True})

        blocked = type(
            "R",
            (),
            {
                "blocked": True,
                "error_message": "blocked",
                "tool_content": "blocked by hook",
                "block_reason": "blocked by hook",
                "tool_output": None,
            },
        )()

        with patch("aiecs.tools.get_tool", return_value=mock_tool):
            agent = HybridAgent(
                agent_id="h1-block",
                name="Block Agent",
                config=AgentConfiguration(llm_model="m"),
                llm_client=_HookSpyLLM(),
                tools=["mock_tool"],
            )

        plugin_ctx = AgentPluginContext(
            agent=agent,
            task={},
            context={},
            task_description="test",
        )
        messages: list[LLMMessage] = []
        state = ToolLoopRunState()

        with patch(
            "aiecs.domain.agent.plugins.hooks.tool_dispatch.dispatch_tool_with_hooks",
            AsyncMock(return_value=blocked),
        ):
            await agent._process_tool_calls_batch(
                thought_raw="thought",
                tool_calls_to_process=[
                    {
                        "id": "call_b",
                        "type": "function",
                        "function": {"name": "mock_tool__query", "arguments": "{}"},
                    }
                ],
                messages=messages,
                iteration=0,
                state=state,
                plugin_ctx=plugin_ctx,
            )

        mock_tool.run_async.assert_not_called()
        assert messages[-1].role == "tool"
        assert messages[-1].content == "blocked by hook"
