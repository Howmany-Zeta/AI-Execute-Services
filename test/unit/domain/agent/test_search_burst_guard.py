"""
Unit tests for search burst guard (M-D.4).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.search_burst_guard import (
    SearchBurstGuardConfig,
    SearchBurstGuardService,
    is_depth_tool,
    is_search_tool,
    resolve_search_burst_guard_config,
)


@pytest.mark.unit
class TestSearchBurstGuardService:
    def test_consecutive_search_fires_at_threshold(self) -> None:
        svc = SearchBurstGuardService(SearchBurstGuardConfig(enabled=True, threshold=3))
        signals = []
        for _ in range(3):
            signal = svc.record_tool_call(tool_name="web_search", operation="search_web")
            if signal is not None:
                signals.append(signal)

        assert len(signals) == 1
        assert signals[0].consecutive_search_count == 3
        assert signals[0].triggered is True
        assert signals[0].reminder is not None
        assert "search_burst_guard" in signals[0].reminder

    def test_different_search_queries_still_accumulate(self) -> None:
        svc = SearchBurstGuardService(SearchBurstGuardConfig(enabled=True, threshold=3))
        signal = None
        for _ in range(3):
            signal = svc.record_tool_call(tool_name="web_search", operation="search_web")
        assert signal is not None
        assert svc.get_signal().consecutive_search_count == 3

    def test_depth_tool_resets_counter(self) -> None:
        svc = SearchBurstGuardService(SearchBurstGuardConfig(enabled=True, threshold=3))
        svc.record_tool_call(tool_name="web_search")
        svc.record_tool_call(tool_name="web_search")
        svc.record_tool_call(tool_name="web_scrape")

        signal = svc.record_tool_call(tool_name="web_search")
        assert signal is None
        assert svc.get_signal().consecutive_search_count == 1

    def test_read_files_resets_counter(self) -> None:
        svc = SearchBurstGuardService(SearchBurstGuardConfig(enabled=True, threshold=3))
        svc.record_tool_call(tool_name="web_search")
        svc.record_tool_call(tool_name="web_search")
        svc.record_tool_call(tool_name="read_files")

        assert svc.get_signal().consecutive_search_count == 0
        signal = svc.record_tool_call(tool_name="web_search")
        assert signal is None
        assert svc.get_signal().consecutive_search_count == 1

    def test_non_search_tools_do_not_reset_or_increment(self) -> None:
        svc = SearchBurstGuardService(SearchBurstGuardConfig(enabled=True, threshold=3))
        svc.record_tool_call(tool_name="web_search")
        svc.record_tool_call(tool_name="chart_tool")
        signal = svc.record_tool_call(tool_name="web_search")
        assert signal is None
        assert svc.get_signal().consecutive_search_count == 2

    def test_disabled_is_noop(self) -> None:
        svc = SearchBurstGuardService(SearchBurstGuardConfig(enabled=False))
        signal = None
        for _ in range(5):
            signal = svc.record_tool_call(tool_name="web_search")
        assert signal is None
        assert svc.get_signal().consecutive_search_count == 0

    def test_hook_only_mode_has_no_reminder(self) -> None:
        svc = SearchBurstGuardService(
            SearchBurstGuardConfig(enabled=True, threshold=2, inject_reminder=False)
        )
        svc.record_tool_call(tool_name="web_search")
        signal = svc.record_tool_call(tool_name="web_search")
        assert signal is not None
        assert signal.reminder is None


@pytest.mark.unit
class TestSearchBurstGuardConfig:
    def test_env_flag_enables_default_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AIECS_SEARCH_BURST_GUARD", "true")
        cfg = resolve_search_burst_guard_config(None)
        assert cfg is not None
        assert cfg.enabled is True
        assert cfg.threshold == 3

    def test_explicit_config_overrides_env_off(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AIECS_SEARCH_BURST_GUARD", raising=False)
        cfg = resolve_search_burst_guard_config({"enabled": True, "threshold": 4})
        assert cfg is not None
        assert cfg.enabled is True
        assert cfg.threshold == 4


@pytest.mark.unit
class TestSearchBurstToolClassification:
    def test_search_tool_detection(self) -> None:
        cfg = SearchBurstGuardConfig()
        assert is_search_tool("web_search", "search_web", cfg) is True
        assert is_search_tool("search", None, cfg) is True
        assert is_search_tool("web_scrape", None, cfg) is False

    def test_depth_tool_detection(self) -> None:
        cfg = SearchBurstGuardConfig()
        assert is_depth_tool("web_scrape", None, cfg) is True
        assert is_depth_tool("read_files", None, cfg) is True


@pytest.mark.unit
class TestHybridAgentSearchBurstIntegration:
    @pytest.mark.asyncio
    async def test_track_search_burst_injects_reminder(self) -> None:
        from aiecs.domain.agent.hybrid_agent import HybridAgent
        from aiecs.domain.agent.models import AgentConfiguration

        agent = HybridAgent(
            agent_id="burst-agent",
            name="Burst",
            tools=[],
            config=AgentConfiguration(
                llm_model="m",
                search_burst_guard={"enabled": True, "threshold": 2, "inject_reminder": True},
            ),
            llm_client=AsyncMock(),
        )
        agent._search_burst_guard = SearchBurstGuardService(
            SearchBurstGuardConfig(enabled=True, threshold=2, inject_reminder=True)
        )
        plugin_ctx = AgentPluginContext(agent=agent, task={}, context={}, task_description="t")

        assert await agent._track_search_burst_guard(
            tool_name="web_search",
            operation="search_web",
            iteration=0,
            plugin_ctx=plugin_ctx,
        ) is None

        reminder = await agent._track_search_burst_guard(
            tool_name="web_search",
            operation="search_web",
            iteration=1,
            plugin_ctx=plugin_ctx,
        )
        assert reminder is not None
        assert "search_burst_guard" in reminder
        assert plugin_ctx.plugin_state["gvr.search_burst_signal"]["triggered"] is True

    @pytest.mark.asyncio
    async def test_track_search_burst_dispatches_hook_when_configured(self) -> None:
        from aiecs.domain.agent.hybrid_agent import HybridAgent
        from aiecs.domain.agent.models import AgentConfiguration

        agent = HybridAgent(
            agent_id="burst-hook-agent",
            name="BurstHook",
            tools=[],
            config=AgentConfiguration(
                llm_model="m",
                search_burst_guard={"enabled": True, "threshold": 2, "hook_on_detect": True},
            ),
            llm_client=AsyncMock(),
        )
        agent._search_burst_guard = SearchBurstGuardService(
            SearchBurstGuardConfig(enabled=True, threshold=2, hook_on_detect=True)
        )
        plugin_ctx = AgentPluginContext(agent=agent, task={}, context={}, task_description="t")

        with patch(
            "aiecs.domain.agent.plugins.hooks.task_boundary.dispatch_search_burst_detected_hook",
            new_callable=AsyncMock,
        ) as dispatch_hook:
            await agent._track_search_burst_guard(
                tool_name="web_search",
                operation="search_web",
                iteration=0,
                plugin_ctx=plugin_ctx,
            )
            await agent._track_search_burst_guard(
                tool_name="web_search",
                operation="search_web",
                iteration=1,
                plugin_ctx=plugin_ctx,
            )

        dispatch_hook.assert_awaited_once()
        assert dispatch_hook.await_args.args[2] == 1
        signal = dispatch_hook.await_args.args[1]
        assert signal.triggered is True
