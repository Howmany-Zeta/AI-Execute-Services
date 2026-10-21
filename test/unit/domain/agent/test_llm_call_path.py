"""Tests for the shortened agent LLM call path (state, retry, streaming, memory)."""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict, List, Optional
from unittest.mock import AsyncMock, patch

import pytest

from aiecs.domain.agent.exceptions import TaskExecutionError
from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.integration.retry_policy import ErrorClassifier, ErrorType
from aiecs.domain.agent.llm_agent import LLMAgent
from aiecs.domain.agent.models import AgentConfiguration, AgentState, RecoveryStrategy, RetryPolicy
from aiecs.domain.agent.plugins.dawp.budget import TaskIterationBudget
from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult, HookResult
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.domain.agent.tool_agent import ToolAgent
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse
from aiecs.llm.clients.base_client import ProviderNotAvailableError, RateLimitError
from aiecs.llm.clients.openai_compatible_mixin import StreamChunk
from aiecs.tools import BaseTool


def _fast_retry(**kwargs: Any) -> RetryPolicy:
    return RetryPolicy(
        max_retries=kwargs.pop("max_retries", 2),
        base_delay=0.0,
        max_delay=0.0,
        jitter_factor=0.0,
        **kwargs,
    )


def _config(*, memory: bool = False, max_retries: int = 2, **kwargs: Any) -> AgentConfiguration:
    plugins = [
        PluginConfig(name="tool", enabled=False),
        PluginConfig(name="skill", enabled=False),
        PluginConfig(name="memory", enabled=memory),
    ]
    return AgentConfiguration(
        goal="llm call path",
        llm_model="test-model",
        retry_policy=_fast_retry(max_retries=max_retries),
        plugins=plugins,
        memory_enabled=memory,
        **kwargs,
    )


def _overloaded_529(message: str = "overloaded") -> ProviderNotAvailableError:
    cause = Exception("provider overloaded")
    cause.status_code = 529  # type: ignore[attr-defined]
    err = ProviderNotAvailableError(message)
    err.__cause__ = cause
    return err


class CountingTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(tool_name="counter")
        self.call_count = 0

    async def run_async(self, op: str | None = None, **kwargs: Any) -> Any:
        self.call_count += 1
        return {"ok": True, "args": kwargs}


class FailingTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(tool_name="failing")

    async def run_async(self, op: str | None = None, **kwargs: Any) -> Any:
        raise RuntimeError("tool exploded")


class ScriptedLLM(BaseLLMClient):
    def __init__(
        self,
        *,
        provider_name: str = "openai",
        retries_generate_text: bool = False,
        generate: Optional[List[Any]] = None,
        stream: Optional[List[Any]] = None,
    ) -> None:
        super().__init__(provider_name=provider_name)
        self.retries_generate_text = retries_generate_text
        self._generate = list(generate or [])
        self._stream = list(stream or [])
        self.generate_calls = 0
        self.stream_opens = 0
        self.last_messages: List[LLMMessage] = []

    async def generate_text(self, messages: List[LLMMessage], model: str | None = None, **kwargs: Any) -> LLMResponse:
        self.generate_calls += 1
        self.last_messages = list(messages)
        if not self._generate:
            return LLMResponse(content="ok", provider=self.provider_name, model=model or "test", tokens_used=1)
        item = self._generate.pop(0)
        if isinstance(item, Exception):
            raise item
        if callable(item):
            item = item()
        if isinstance(item, Exception):
            raise item
        if isinstance(item, LLMResponse):
            return item
        response = LLMResponse(
            content=item.get("content", ""),
            provider=self.provider_name,
            model=model or "test",
            tokens_used=item.get("tokens_used", 1),
        )
        if item.get("tool_calls") is not None:
            response.tool_calls = item["tool_calls"]
        if item.get("cache_read_tokens") is not None:
            response.cache_read_tokens = item["cache_read_tokens"]
        return response

    async def stream_text(self, messages: List[LLMMessage], model: str | None = None, **kwargs: Any) -> AsyncIterator[Any]:
        self.stream_opens += 1
        self.last_messages = list(messages)
        if not self._stream:
            yield StreamChunk(type="token", content="ok")
            return
        item = self._stream.pop(0)
        if isinstance(item, Exception):
            raise item
        if callable(item):
            item = item()
        if isinstance(item, Exception):
            raise item
        for chunk in item:
            if isinstance(chunk, Exception):
                raise chunk
            yield chunk

    async def close(self) -> None:
        return None


def _tool_call(name: str, arguments: Optional[Dict[str, Any]] = None, call_id: str = "call_0") -> Dict[str, Any]:
    import json

    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments or {})},
    }


async def _init_llm(client: BaseLLMClient, **config_kwargs: Any) -> LLMAgent:
    agent = LLMAgent(
        agent_id="llm-call-path",
        name="LLM",
        llm_client=client,
        config=_config(**config_kwargs),
    )
    await agent.initialize()
    return agent


async def _init_tool(
    client: BaseLLMClient,
    tools: Optional[Dict[str, BaseTool]] = None,
    **config_kwargs: Any,
) -> ToolAgent:
    agent = ToolAgent(
        agent_id="tool-call-path",
        name="Tool",
        llm_client=client,
        tools=tools or {"counter": CountingTool()},
        config=_config(**config_kwargs),
    )
    await agent.initialize()
    return agent


async def _init_hybrid(
    client: BaseLLMClient,
    tools: Optional[Dict[str, BaseTool]] = None,
    **config_kwargs: Any,
) -> HybridAgent:
    agent = HybridAgent(
        agent_id="hybrid-call-path",
        name="Hybrid",
        llm_client=client,
        tools=tools if tools is not None else {},
        config=_config(**config_kwargs),
        max_iterations=5,
    )
    await agent.initialize()
    return agent


async def _collect(agen) -> List[Any]:
    items: List[Any] = []
    async for item in agen:
        items.append(item)
    return items


@pytest.mark.unit
class TestErrorClassifier:
    def test_rate_limit_type(self) -> None:
        assert ErrorClassifier.classify(RateLimitError("slow down")) == ErrorType.RATE_LIMIT

    def test_status_529_on_cause(self) -> None:
        assert ErrorClassifier.classify(_overloaded_529()) == ErrorType.SERVER_ERROR
        assert ErrorClassifier.is_retryable(ErrorType.SERVER_ERROR)

    def test_prompt_too_long_is_client_error(self) -> None:
        err = RuntimeError("prompt too long: context length exceeded")
        assert ErrorClassifier.classify(err) == ErrorType.CLIENT_ERROR
        assert not ErrorClassifier.is_retryable(ErrorType.CLIENT_ERROR)


@pytest.mark.unit
@pytest.mark.asyncio
class TestStateRecover:
    async def test_hybrid_prompt_hook_reject_returns_active(self) -> None:
        client = ScriptedLLM(generate=[{"content": "should not run"}])
        agent = await _init_hybrid(client)
        rejected = AggregatedHookResult(
            results=[HookResult(hook_type="user_prompt_submit", success=True, continue_allowed=False, reason="blocked")]
        )
        with patch.object(agent, "_build_tool_loop_compression_context_async", wraps=agent._build_tool_loop_compression_context_async):
            with patch(
                "aiecs.domain.agent.hybrid_agent.prepare_and_dispatch_task_entry_hooks",
                AsyncMock(return_value=rejected),
            ):
                events = await _collect(agent.execute_task_streaming({"description": "blocked"}, {}))
        assert agent.state == AgentState.ACTIVE
        assert agent._current_task_id is None
        assert any(event.get("type") == "result" for event in events)
        await agent.reload_plugins()
        result = await agent.execute_task({"description": "next"}, {})
        assert result.get("success") is True
        assert agent.state == AgentState.ACTIVE

    @pytest.mark.parametrize("factory", [_init_llm, _init_hybrid])
    async def test_aclose_after_busy_returns_active(self, factory) -> None:
        hang = asyncio.Event()

        class HangLLM(ScriptedLLM):
            async def stream_text(self, messages, model=None, **kwargs):
                self.stream_opens += 1
                yield StreamChunk(type="token", content="hi")
                await hang.wait()

        agent = await factory(HangLLM())
        gen = agent.execute_task_streaming({"description": "hang"}, {})
        first = await gen.__anext__()
        assert first.get("type") in {"started", "status"}
        await gen.__anext__()
        await gen.aclose()
        assert agent.state == AgentState.ACTIVE
        assert agent._current_task_id is None

    async def test_success_does_not_double_transition_active(self) -> None:
        agent = await _init_llm(ScriptedLLM(generate=[{"content": "done"}]))
        result = await agent.execute_task({"description": "ok"}, {})
        assert result["success"] is True
        assert agent.state == AgentState.ACTIVE
        result = await agent.execute_task({"description": "again"}, {})
        assert result["success"] is True
        assert agent.state == AgentState.ACTIVE

    async def test_error_state_refuses_task(self) -> None:
        agent = await _init_llm(ScriptedLLM())
        agent._state = AgentState.ERROR
        with pytest.raises(TaskExecutionError, match="not ready"):
            await agent.execute_task({"description": "no"}, {})
        assert agent.state == AgentState.ERROR

    async def test_failure_returns_active_then_next_message_enters_busy(self) -> None:
        client = ScriptedLLM(generate=[RuntimeError("boom"), {"content": "recovered"}])
        agent = await _init_llm(client)
        with pytest.raises(TaskExecutionError):
            await agent.execute_task({"description": "fail"}, {})
        assert agent.state == AgentState.ACTIVE
        entered: List[AgentState] = []
        original = agent._transition_state

        def _spy(new_state):
            entered.append(new_state)
            return original(new_state)

        agent._transition_state = _spy  # type: ignore[method-assign]
        result = await agent.execute_task({"description": "retry"}, {})
        assert AgentState.BUSY in entered
        assert result["success"] is True
        assert agent.state == AgentState.ACTIVE

    async def test_toolagent_direct_tool_error_emits_and_stays_active(self) -> None:
        agent = await _init_tool(ScriptedLLM(), tools={"failing": FailingTool()})
        events = await _collect(
            agent.execute_task_streaming({"tool": "failing", "operation": "run", "parameters": {}}, {})
        )
        assert any(event.get("type") == "error" for event in events)
        assert agent.state == AgentState.ACTIVE


@pytest.mark.unit
@pytest.mark.asyncio
class TestRecoveryRetryOnce:
    async def test_default_chain_starts_with_retry(self) -> None:
        agent = await _init_llm(ScriptedLLM(generate=[{"content": "ok"}]))
        seen: List[str] = []

        async def _execute(task, context):
            seen.append("execute")
            return {"success": True, "output": "ok"}

        agent.execute_task = _execute  # type: ignore[method-assign]
        agent._simplify_task = AsyncMock(side_effect=AssertionError("SIMPLIFY must not run"))  # type: ignore[method-assign]
        result = await agent.execute_with_recovery({"description": "orig"}, {})
        assert result["success"] is True
        assert seen == ["execute"]

    async def test_retry_calls_execute_task_once(self) -> None:
        agent = await _init_llm(ScriptedLLM())
        calls: List[str] = []

        async def _execute(task, context):
            calls.append(task["description"])
            return {"success": True, "output": "ok"}

        agent.execute_task = _execute  # type: ignore[method-assign]
        await agent.execute_with_recovery(
            {"description": "orig"},
            {},
            strategies=[RecoveryStrategy.RETRY, RecoveryStrategy.SIMPLIFY],
        )
        assert calls == ["orig"]

    async def test_retry_failure_then_simplify(self) -> None:
        agent = await _init_llm(ScriptedLLM())
        calls: List[str] = []

        async def _execute(task, context):
            calls.append(task["description"])
            if task["description"] == "orig":
                raise TaskExecutionError("first failed")
            return {"success": True, "output": "simplified"}

        agent.execute_task = _execute  # type: ignore[method-assign]
        agent._simplify_task = AsyncMock(return_value={"description": "simple"})  # type: ignore[method-assign]
        result = await agent.execute_with_recovery(
            {"description": "orig"},
            {},
            strategies=[RecoveryStrategy.RETRY, RecoveryStrategy.SIMPLIFY],
        )
        assert calls == ["orig", "simple"]
        assert result["success"] is True

    async def test_streaming_retry_calls_execute_task_streaming_once(self) -> None:
        agent = await _init_llm(ScriptedLLM())
        calls = 0

        async def _stream(task, context):
            nonlocal calls
            calls += 1
            yield {"type": "token", "content": "hi"}
            yield {"type": "result", "success": True, "output": "hi"}

        agent.execute_task_streaming = _stream  # type: ignore[method-assign]
        await _collect(
            agent.execute_with_recovery_streaming(
                {"description": "orig"},
                {},
                strategies=[RecoveryStrategy.RETRY, RecoveryStrategy.SIMPLIFY],
            )
        )
        assert calls == 1


@pytest.mark.unit
@pytest.mark.asyncio
class TestSingleRetryLayer:
    async def test_client_retries_generate_text_not_wrapped(self) -> None:
        client = ScriptedLLM(retries_generate_text=True, generate=[RateLimitError("429")])
        agent = await _init_llm(client)
        with pytest.raises(TaskExecutionError):
            await agent.execute_task({"description": "rate"}, {})
        assert client.generate_calls == 1

    async def test_agent_retries_429_then_tool_once(self) -> None:
        tool = CountingTool()
        client = ScriptedLLM(
            retries_generate_text=False,
            generate=[
                RateLimitError("429"),
                {"content": "using tool", "tool_calls": [_tool_call("counter", {"q": "1"})]},
            ],
        )
        agent = await _init_tool(client, tools={"counter": tool})
        result = await agent.execute_task({"description": "use tool"}, {})
        assert client.generate_calls == 2
        assert tool.call_count == 1
        assert result["success"] is True

    async def test_529_uses_max_retries_plus_one(self) -> None:
        client = ScriptedLLM(
            retries_generate_text=False,
            generate=[_overloaded_529(), _overloaded_529(), _overloaded_529()],
        )
        agent = await _init_llm(client, max_retries=2)
        with pytest.raises(TaskExecutionError):
            await agent.execute_task({"description": "overloaded"}, {})
        assert client.generate_calls == 3

    async def test_stream_reopens_max_retries_plus_one(self) -> None:
        client = ScriptedLLM(
            stream=[_overloaded_529(), _overloaded_529(), _overloaded_529()],
        )
        agent = await _init_llm(client, max_retries=2)
        events = await _collect(agent.execute_task_streaming({"description": "stream 529"}, {}))
        assert any(event.get("type") == "error" for event in events)
        assert client.stream_opens == 3

    async def test_stream_handoff_does_not_reopen_or_process_tools(self) -> None:
        tool = CountingTool()
        client = ScriptedLLM(
            stream=[[StreamChunk(type="token", content="hi"), TimeoutError("timeout after token")]],
        )
        agent = await _init_hybrid(client, tools={"counter": tool})
        processed = AsyncMock()
        agent._process_tool_calls_batch = processed  # type: ignore[method-assign]
        consumes: List[int] = []
        original = TaskIterationBudget.consume

        def _consume(self, n: int = 1) -> None:
            consumes.append(n)
            return original(self, n)

        with patch.object(TaskIterationBudget, "consume", _consume):
            events = await _collect(agent.execute_task_streaming({"description": "partial"}, {}))
        assert client.stream_opens == 1
        processed.assert_not_called()
        assert consumes == []
        assert tool.call_count == 0
        assert any(event.get("type") == "error" for event in events)
        assistant_roles = [m.role for m in client.last_messages if m.role == "assistant"]
        assert assistant_roles == []

    async def test_ptl_compact_uses_call_llm_once(self) -> None:
        client = ScriptedLLM(
            retries_generate_text=False,
            generate=[RuntimeError("prompt too long"), {"content": "compacted ok"}],
        )
        agent = await _init_hybrid(client)
        call_llm = AsyncMock(wraps=agent._call_llm)
        agent._call_llm = call_llm  # type: ignore[method-assign]
        with patch(
            "aiecs.domain.agent.hybrid_agent.maybe_reactive_compact_on_ptl",
            AsyncMock(return_value=True),
        ):
            result = await agent.execute_task({"description": "long"}, {})
        assert result["success"] is True
        assert call_llm.await_count == 2
        assert client.generate_calls == 2

    async def test_ptl_second_failure_is_not_ordinary_retry(self) -> None:
        client = ScriptedLLM(
            retries_generate_text=False,
            generate=[RuntimeError("prompt too long"), RuntimeError("prompt too long")],
        )
        agent = await _init_hybrid(client)
        with patch(
            "aiecs.domain.agent.hybrid_agent.maybe_reactive_compact_on_ptl",
            AsyncMock(return_value=True),
        ):
            with pytest.raises(TaskExecutionError):
                await agent.execute_task({"description": "still long"}, {})
        assert client.generate_calls == 2

    async def test_ptl_stream_compact_uses_stream_llm(self) -> None:
        client = ScriptedLLM(
            stream=[
                RuntimeError("prompt too long"),
                [StreamChunk(type="token", content="after compact")],
            ],
        )
        agent = await _init_hybrid(client)
        stream_llm = agent._stream_llm
        calls = 0

        async def _wrapped(*args, **kwargs):
            nonlocal calls
            calls += 1
            async for chunk in stream_llm(*args, **kwargs):
                yield chunk

        agent._stream_llm = _wrapped  # type: ignore[method-assign]
        with patch(
            "aiecs.domain.agent.hybrid_agent.maybe_reactive_compact_on_ptl",
            AsyncMock(return_value=True),
        ):
            events = await _collect(agent.execute_task_streaming({"description": "long stream"}, {}))
        assert calls == 2
        assert client.stream_opens == 2
        assert any(event.get("type") == "token" and event.get("content") == "after compact" for event in events)

    async def test_stream_chunk_passthrough_and_cache_once(self) -> None:
        chunk = StreamChunk(
            type="token",
            content="x",
            thought_signature="sig",
            tool_calls=[{"id": "c1"}],
            usage={"cache_read_tokens": 7},
        )
        usage = StreamChunk(type="usage", usage={"cache_read_tokens": 11})
        client = ScriptedLLM(stream=[[chunk, usage]])
        agent = await _init_llm(client)
        cache_calls: List[Any] = []
        original = agent.record_prompt_cache

        def _record(*args, **kwargs):
            cache_calls.append((args, kwargs))
            return original(*args, **kwargs)

        agent.record_prompt_cache = _record  # type: ignore[method-assign]
        yielded: List[Any] = []
        async for item in agent._stream_llm([LLMMessage(role="user", content="hi")], {}):
            yielded.append(item)
        assert yielded[0] is chunk
        assert yielded[0].thought_signature == "sig"
        assert yielded[0].tool_calls == [{"id": "c1"}]
        assert yielded[0].usage == {"cache_read_tokens": 7}
        assert cache_calls == []

        client._stream = [[StreamChunk(type="token", content="y"), usage]]
        events = await _collect(agent.execute_task_streaming({"description": "cache"}, {}))
        assert len(cache_calls) == 1
        assert any(event.get("type") == "result" for event in events)

    async def test_toolagent_fallback_token(self) -> None:
        client = ScriptedLLM(
            stream=[[StreamChunk(type="usage", usage={"content": "full body", "cache_read_tokens": 0})]],
        )
        agent = await _init_tool(client)
        events = await _collect(agent.execute_task_streaming({"description": "vertex empty stream"}, {}))
        tokens = [event for event in events if event.get("type") == "token"]
        assert len(tokens) == 1
        assert tokens[0].get("is_fallback") is True
        assert tokens[0]["content"] == "full body"

    async def test_second_round_failure_does_not_replay_tools_or_budget(self) -> None:
        tool = CountingTool()
        client = ScriptedLLM(
            stream=[
                [
                    StreamChunk(type="token", content="call tool"),
                    StreamChunk(type="tool_calls", tool_calls=[_tool_call("counter")]),
                ],
                [StreamChunk(type="token", content="round2"), TimeoutError("timeout after success")],
            ],
        )
        agent = await _init_hybrid(client, tools={"counter": tool})
        consumes: List[int] = []
        original = TaskIterationBudget.consume

        def _consume(self, n: int = 1) -> None:
            consumes.append(n)
            return original(self, n)

        with patch.object(TaskIterationBudget, "consume", _consume):
            events = await _collect(agent.execute_task_streaming({"description": "two rounds"}, {}))
        assert tool.call_count == 1
        assert consumes == [1]
        assert any(event.get("type") == "error" for event in events)

    async def test_compression_context_built_once_per_task(self) -> None:
        tool = CountingTool()
        client = ScriptedLLM(
            generate=[
                {"content": "tool", "tool_calls": [_tool_call("counter")]},
                {"content": "done"},
            ],
        )
        agent = await _init_hybrid(client, tools={"counter": tool})
        with patch.object(
            agent,
            "_build_tool_loop_compression_context_async",
            wraps=agent._build_tool_loop_compression_context_async,
        ) as built:
            result = await agent.execute_task({"description": "two iters"}, {})
        assert result["success"] is True
        assert built.await_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
class TestAlignStreaming:
    async def test_toolagent_last_tool_failure_is_not_success(self) -> None:
        client = ScriptedLLM(
            generate=[{"content": "failing", "tool_calls": [_tool_call("failing")]}],
        )
        agent = await _init_tool(client, tools={"failing": FailingTool()})
        result = await agent.execute_task({"description": "fail last tool"}, {})
        assert result["success"] is False
        assert "exploded" in str(result.get("output"))

    async def test_llm_and_tool_use_same_build_messages(self) -> None:
        llm = await _init_llm(ScriptedLLM(generate=[{"content": "s"}, {"content": "s"}]))
        tool = await _init_tool(
            ScriptedLLM(generate=[{"content": "s"}, {"content": "s"}]),
        )
        with patch.object(llm, "_build_messages_via_plugins", wraps=llm._build_messages_via_plugins) as llm_build:
            await llm.execute_task({"description": "sync"}, {})
            await _collect(llm.execute_task_streaming({"description": "stream"}, {}))
        with patch.object(tool, "_build_messages_via_plugins", wraps=tool._build_messages_via_plugins) as tool_build:
            await tool.execute_task({"description": "sync"}, {})
            await _collect(tool.execute_task_streaming({"description": "stream"}, {}))
        assert llm_build.await_count == 2
        assert tool_build.await_count == 2

    async def test_memory_writes_one_turn_per_complete_task(self) -> None:
        llm = await _init_llm(
            ScriptedLLM(generate=[{"content": "sync-a"}], stream=[[StreamChunk(type="token", content="stream-a")]]),
            memory=True,
        )
        tool = await _init_tool(
            ScriptedLLM(generate=[{"content": "sync-b"}], stream=[[StreamChunk(type="token", content="stream-b")]]),
            memory=True,
        )
        await llm.execute_task({"description": "sync llm"}, {"session_id": "s1"})
        await _collect(llm.execute_task_streaming({"description": "stream llm"}, {"session_id": "s1"}))
        users = [m for m in llm._conversation_history if m.role == "user"]
        assistants = [m for m in llm._conversation_history if m.role == "assistant"]
        assert len(users) == 2
        assert len(assistants) == 2

        await tool.execute_task({"description": "sync tool"}, {"session_id": "s2"})
        await _collect(tool.execute_task_streaming({"description": "stream tool"}, {"session_id": "s2"}))
        users = [m for m in tool._conversation_history if m.role == "user"]
        assistants = [m for m in tool._conversation_history if m.role == "assistant"]
        assert len(users) == 2
        assert len(assistants) == 2

    async def test_hybrid_streaming_memory_one_turn(self) -> None:
        agent = await _init_hybrid(
            ScriptedLLM(stream=[[StreamChunk(type="token", content="hello")]]),
            memory=True,
        )
        await _collect(agent.execute_task_streaming({"description": "hi"}, {"session_id": "hy1"}))
        plugin = agent._plugin_manager.get_plugin("memory") if agent._plugin_manager else None
        history = await plugin.get_history("hy1") if plugin is not None else []
        users = [m for m in history if m.role == "user"]
        assistants = [m for m in history if m.role == "assistant"]
        assert len(users) == 1
        assert len(assistants) == 1

    async def test_aclose_does_not_write_partial_memory(self) -> None:
        hang = asyncio.Event()

        class HangLLM(ScriptedLLM):
            async def stream_text(self, messages, model=None, **kwargs):
                yield StreamChunk(type="token", content="partial")
                await hang.wait()

        agent = await _init_llm(HangLLM(), memory=True)
        gen = agent.execute_task_streaming({"description": "partial"}, {"session_id": "p1"})
        await gen.__anext__()
        await gen.__anext__()
        await gen.aclose()
        assert agent._conversation_history == []

    @pytest.mark.parametrize("factory", [_init_llm, _init_tool, _init_hybrid])
    async def test_process_message_streaming_raises_on_error(self, factory) -> None:
        agent = await factory(ScriptedLLM())

        async def _err(task, context):
            yield {"type": "error", "error": "stream failed"}

        agent.execute_task_streaming = _err  # type: ignore[method-assign]
        with pytest.raises(TaskExecutionError, match="stream failed"):
            await _collect(agent.process_message_streaming("hello"))

    @pytest.mark.parametrize("factory", [_init_llm, _init_tool, _init_hybrid])
    async def test_process_message_streaming_yields_result_output_once(self, factory) -> None:
        agent = await factory(ScriptedLLM())

        async def _result_only(task, context):
            yield {"type": "result", "output": "body only"}

        agent.execute_task_streaming = _result_only  # type: ignore[method-assign]
        tokens = await _collect(agent.process_message_streaming("hello"))
        assert tokens == ["body only"]

    @pytest.mark.parametrize("factory", [_init_llm, _init_tool, _init_hybrid])
    async def test_process_message_streaming_does_not_repeat_result(self, factory) -> None:
        agent = await factory(ScriptedLLM())

        async def _tokens(task, context):
            yield {"type": "token", "content": "hi"}
            yield {"type": "result", "output": "hi there"}

        agent.execute_task_streaming = _tokens  # type: ignore[method-assign]
        tokens = await _collect(agent.process_message_streaming("hello"))
        assert tokens == ["hi"]
