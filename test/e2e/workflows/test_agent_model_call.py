"""
E2E: LLMAgent, ToolAgent, and HybridAgent each call a real model and get text.

Requires XAI_API_KEY (same provider as the agent integration suite).
"""

from __future__ import annotations

from typing import Any

import pytest

from aiecs.domain.agent import AgentConfiguration, HybridAgent, LLMAgent, ToolAgent
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.llm import XAIClient
from aiecs.tools import BaseTool
from test.e2e.base import E2ELLMTestBase, log_test_info


PROMPT = "Reply with just the word OK."


class EchoTool(BaseTool):
    """Local no-network tool so ToolAgent/HybridAgent can enter LLM mode."""

    async def echo(self, text: str = "") -> dict[str, str]:
        return {"echo": text or "ok"}


def _agent_config() -> AgentConfiguration:
    return AgentConfiguration(
        goal="E2E model call",
        llm_model="grok-3-mini",
        temperature=0.0,
        max_tokens=32,
        memory_enabled=False,
        plugins=[
            PluginConfig(name="tool", enabled=False),
            PluginConfig(name="skill", enabled=False),
            PluginConfig(name="memory", enabled=False),
        ],
    )


def _text_from_result(result: dict[str, Any]) -> str:
    for key in ("output", "llm_response", "final_response"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if value is not None and not isinstance(value, str):
            text = str(value).strip()
            if text:
                return text
    return ""


def _skip_if_provider_unavailable(exc: BaseException) -> None:
    text = str(exc).lower()
    needles = (
        "permission-denied",
        "permissiondenied",
        "spending limit",
        "used all available credits",
        "insufficient credits",
        "401",
        "403",
    )
    if any(needle in text for needle in needles):
        pytest.skip(f"LLM provider unavailable: {exc}")


@pytest.mark.e2e
@pytest.mark.xai
@pytest.mark.requires_api
class TestAgentModelCallE2E(E2ELLMTestBase):
    """Three agent types call a real model and receive text."""

    @pytest.fixture(autouse=True)
    def setup(self, xai_api_key, cost_tracker):
        self.api_key = xai_api_key
        self.cost_tracker = cost_tracker
        self.model = "grok-3-mini"

    def _client(self) -> XAIClient:
        return XAIClient()

    async def _llm_agent(self) -> LLMAgent:
        agent = LLMAgent(
            agent_id="e2e-llm",
            name="E2E LLM",
            llm_client=self._client(),
            config=_agent_config(),
        )
        await agent.initialize()
        return agent

    async def _tool_agent(self) -> ToolAgent:
        agent = ToolAgent(
            agent_id="e2e-tool",
            name="E2E Tool",
            llm_client=self._client(),
            tools={"echo": EchoTool()},
            config=_agent_config(),
        )
        await agent.initialize()
        return agent

    async def _hybrid_agent(self) -> HybridAgent:
        agent = HybridAgent(
            agent_id="e2e-hybrid",
            name="E2E Hybrid",
            llm_client=self._client(),
            tools={"echo": EchoTool()},
            config=_agent_config(),
            max_iterations=3,
        )
        await agent.initialize()
        return agent

    @pytest.mark.asyncio
    @pytest.mark.parametrize("factory", ["_llm_agent", "_tool_agent", "_hybrid_agent"])
    async def test_execute_task_returns_text(self, factory: str) -> None:
        log_test_info(f"{factory} execute_task", model=self.model, prompt=PROMPT)
        agent = await getattr(self, factory)()
        try:
            result, latency = await self.measure_latency_async(
                agent.execute_task,
                {"description": PROMPT},
                {},
            )
        except Exception as exc:
            _skip_if_provider_unavailable(exc)
            raise
        text = _text_from_result(result)
        self.assert_llm_response_valid(text)
        assert result.get("success") is True
        assert latency < 45.0, f"{factory} took {latency:.2f}s"
        self.record_usage(len(PROMPT.split()), len(text.split()), self.model, self.cost_tracker)
        print(f"\n✅ {factory} execute_task in {latency:.2f}s: {text[:80]}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("factory", ["_llm_agent", "_tool_agent", "_hybrid_agent"])
    async def test_process_message_streaming_returns_text(self, factory: str) -> None:
        log_test_info(f"{factory} process_message_streaming", model=self.model, prompt=PROMPT)
        agent = await getattr(self, factory)()
        tokens: list[str] = []

        async def _collect() -> str:
            async for token in agent.process_message_streaming(PROMPT):
                tokens.append(str(token))
            return "".join(tokens).strip()

        try:
            text, latency = await self.measure_latency_async(_collect)
        except Exception as exc:
            _skip_if_provider_unavailable(exc)
            raise
        self.assert_llm_response_valid(text)
        assert latency < 45.0, f"{factory} streaming took {latency:.2f}s"
        self.record_usage(len(PROMPT.split()), len(text.split()), self.model, self.cost_tracker)
        print(f"\n✅ {factory} streaming in {latency:.2f}s: {text[:80]}")
