"""
Unit tests for hook executor (H0-06).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
from aiecs.domain.agent.plugins.hooks.executor import AgentHookExecutionContext, AgentHookExecutor
from aiecs.domain.agent.plugins.hooks.registry import AgentHookRegistry
from aiecs.domain.agent.plugins.hooks.schemas import CommandHookDefinition, HttpHookDefinition


@pytest.mark.unit
class TestHookExecutor:
    @pytest.mark.asyncio
    async def test_command_hook_uses_stdin_no_shell(self, tmp_path: Path) -> None:
        script = tmp_path / "audit.py"
        script.write_text(
            "import json, sys\npayload = json.load(sys.stdin)\nprint(payload.get('tool_name', ''))\n",
            encoding="utf-8",
        )
        registry = AgentHookRegistry()
        registry.register(
            AgentHookEvent.PRE_TOOL_USE,
            CommandHookDefinition(command=["python", str(script)]),
        )
        executor = AgentHookExecutor(
            registry,
            AgentHookExecutionContext(cwd=tmp_path),
        )
        payload = {"tool_name": "read_file", "tool_input": {"path": "`id`"}}
        result = await executor.execute_event(AgentHookEvent.PRE_TOOL_USE, payload)
        assert result.results[0].success is True
        assert "read_file" in result.results[0].output

    @pytest.mark.asyncio
    async def test_command_hook_env_does_not_inherit_parent_secret(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "super-secret")
        script = tmp_path / "env_check.py"
        script.write_text(
            "import json, os, sys\njson.load(sys.stdin)\nprint('AWS' in os.environ)\n",
            encoding="utf-8",
        )
        registry = AgentHookRegistry()
        registry.register(
            AgentHookEvent.PRE_TOOL_USE,
            CommandHookDefinition(command=["python", str(script)]),
        )
        executor = AgentHookExecutor(
            registry,
            AgentHookExecutionContext(cwd=tmp_path),
        )
        result = await executor.execute_event(AgentHookEvent.PRE_TOOL_USE, {"tool_name": "x"})
        assert result.results[0].success is True
        assert result.results[0].output.strip() == "False"

    @pytest.mark.asyncio
    async def test_http_host_allowlist_blocks(self) -> None:
        registry = AgentHookRegistry()
        registry.register(
            AgentHookEvent.POST_TOOL_USE,
            HttpHookDefinition(url="https://blocked.example/hook", block_on_failure=True),
        )
        executor = AgentHookExecutor(
            registry,
            AgentHookExecutionContext(cwd=Path.cwd(), hook_allowed_http_hosts=frozenset()),
        )
        result = await executor.execute_event(AgentHookEvent.POST_TOOL_USE, {"tool_name": "x"})
        assert result.blocked is True

    @pytest.mark.asyncio
    async def test_matcher_empty_matches_all(self) -> None:
        registry = AgentHookRegistry()
        registry.register(
            AgentHookEvent.PRE_TOOL_USE,
            HttpHookDefinition(url="https://example.com/hook"),
        )
        executor = AgentHookExecutor(
            registry,
            AgentHookExecutionContext(cwd=Path.cwd(), hook_allowed_http_hosts=frozenset({"example.com"})),
        )
        # Will fail HTTP but matcher should not filter
        result = await executor.execute_event(AgentHookEvent.PRE_TOOL_USE, {"tool_name": "anything"})
        assert len(result.results) == 1

    @pytest.mark.asyncio
    async def test_matcher_read_glob(self) -> None:
        registry = AgentHookRegistry()
        registry.register(
            AgentHookEvent.PRE_TOOL_USE,
            HttpHookDefinition(url="https://example.com/hook", matcher="read_*"),
        )
        executor = AgentHookExecutor(
            registry,
            AgentHookExecutionContext(cwd=Path.cwd(), hook_allowed_http_hosts=frozenset()),
        )
        matched = await executor.execute_event(
            AgentHookEvent.PRE_TOOL_USE,
            {"tool_name": "read_file"},
        )
        unmatched = await executor.execute_event(
            AgentHookEvent.PRE_TOOL_USE,
            {"tool_name": "write_file"},
        )
        assert len(matched.results) == 1
        assert unmatched.results == []

    @pytest.mark.asyncio
    async def test_serial_execution_all_hooks_run_even_after_block(self) -> None:
        """Product expectation: block does not short-circuit later hooks (§5.1.3, HOOKS.md)."""
        calls: list[str] = []

        class SpyExecutor(AgentHookExecutor):
            async def _run_http_hook(  # type: ignore[override]
                self, hook, event, payload, *, timeout_seconds: float | None = None
            ):
                del event, payload, timeout_seconds
                calls.append(hook.url)
                blocked = "block" in hook.url
                from aiecs.domain.agent.plugins.hooks.types import HookResult

                return HookResult(
                    hook_type="http",
                    success=not blocked,
                    blocked=blocked,
                    reason="blocked" if blocked else "",
                )

        registry = AgentHookRegistry()
        registry.register(
            AgentHookEvent.PRE_TOOL_USE,
            HttpHookDefinition(url="https://example.com/block", priority=10, block_on_failure=True),
        )
        registry.register(
            AgentHookEvent.PRE_TOOL_USE,
            HttpHookDefinition(url="https://example.com/audit", priority=0),
        )
        executor = SpyExecutor(registry, AgentHookExecutionContext(cwd=Path.cwd()))
        result = await executor.execute_event(AgentHookEvent.PRE_TOOL_USE, {"tool_name": "x"})
        assert result.blocked is True
        assert calls == ["https://example.com/block", "https://example.com/audit"]

    @pytest.mark.asyncio
    async def test_event_timeout_stops_remaining_hooks(self) -> None:
        calls: list[str] = []

        class SlowExecutor(AgentHookExecutor):
            async def _run_http_hook(  # type: ignore[override]
                self,
                hook,
                event,
                payload,
                *,
                timeout_seconds: float | None = None,
            ):
                del event, payload, timeout_seconds
                calls.append(hook.url)
                await asyncio.sleep(0.08)
                from aiecs.domain.agent.plugins.hooks.types import HookResult

                return HookResult(hook_type="http", success=True)

        registry = AgentHookRegistry()
        for index in range(3):
            registry.register(
                AgentHookEvent.PRE_TOOL_USE,
                HttpHookDefinition(url=f"https://example.com/hook-{index}", timeout_seconds=30),
            )
        executor = SlowExecutor(
            registry,
            AgentHookExecutionContext(cwd=Path.cwd(), event_timeout_seconds=0.10),
        )
        result = await executor.execute_event(AgentHookEvent.PRE_TOOL_USE, {"tool_name": "x"})

        assert len(calls) == 2
        assert result.blocked is True
        assert any("event hook chain exceeded" in (item.reason or "") for item in result.results)
