"""
Cross-cutting tests for §11 matrix (sections 6–6 completion gate).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent import AgentConfiguration
from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
from aiecs.domain.agent.plugins.hooks.executor import (
    AgentHookExecutionContext,
    AgentHookExecutor,
    _inject_arguments,
)
from aiecs.domain.agent.plugins.hooks.loader import HookLoadOptions, load_hooks_from_json, normalize_event_key
from aiecs.domain.agent.plugins.hooks.registry import AgentHookRegistry
from aiecs.domain.agent.plugins.hooks.schemas import CommandHookDefinition, HttpHookDefinition, PromptHookDefinition
from aiecs.domain.agent.plugins.hooks.tool_dispatch import dispatch_tool_with_hooks
from aiecs.domain.agent.plugins.hooks.types import HookResult
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.domain.agent.plugins.testing.parity import (
    ParityCase,
    capture_parity_case,
    compare_parity_expect,
    load_parity_fixture,
)
from aiecs.domain.agent.tool_agent import ToolAgent
from aiecs.llm import BaseLLMClient, LLMResponse
from aiecs.tools.base_tool import BaseTool

_FIXTURES = Path(__file__).resolve().parents[6] / "tests" / "fixtures" / "plugin_parity"


@pytest.mark.unit
class TestMatcherAndHttp:
    @pytest.mark.asyncio
    async def test_matcher_mcp_glob(self) -> None:
        registry = AgentHookRegistry()
        registry.register(
            AgentHookEvent.PRE_TOOL_USE,
            HttpHookDefinition(url="https://example.com/hook", matcher="mcp__*"),
        )
        executor = AgentHookExecutor(
            registry,
            AgentHookExecutionContext(cwd=Path.cwd(), hook_allowed_http_hosts=frozenset()),
        )
        matched = await executor.execute_event(
            AgentHookEvent.PRE_TOOL_USE,
            {"tool_name": "mcp__filesystem__read"},
        )
        unmatched = await executor.execute_event(
            AgentHookEvent.PRE_TOOL_USE,
            {"tool_name": "read_file"},
        )
        assert len(matched.results) == 1
        assert unmatched.results == []

    @pytest.mark.asyncio
    async def test_http_5xx_blocks_when_block_on_failure(self) -> None:
        registry = AgentHookRegistry()
        registry.register(
            AgentHookEvent.POST_TOOL_USE,
            HttpHookDefinition(
                url="https://example.com/hook",
                block_on_failure=True,
            ),
        )
        executor = AgentHookExecutor(
            registry,
            AgentHookExecutionContext(
                cwd=Path.cwd(),
                hook_allowed_http_hosts=frozenset({"example.com"}),
            ),
        )

        response = MagicMock()
        response.is_success = False
        response.status_code = 503
        response.text = "service unavailable"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("aiecs.domain.agent.plugins.hooks.executor.httpx.AsyncClient", return_value=mock_client):
            result = await executor.execute_event(AgentHookEvent.POST_TOOL_USE, {"tool_name": "x"})

        assert result.blocked is True
        assert result.results[0].metadata.get("status_code") == 503


@pytest.mark.unit
class TestPromptAndCommandArguments:
    def test_prompt_arguments_json_embed(self) -> None:
        payload = {"tool_name": "search", "tool_input": {"q": "hooks"}}
        injected = _inject_arguments("Audit payload: $ARGUMENTS", payload)
        assert "$ARGUMENTS" not in injected
        assert json.loads(injected.split(": ", 1)[1]) == payload

    @pytest.mark.asyncio
    async def test_command_hook_uses_stdin_not_arguments_template(self, tmp_path: Path) -> None:
        script = tmp_path / "stdin_only.py"
        script.write_text(
            "import json, sys\n"
            "payload = json.load(sys.stdin)\n"
            "print(payload['tool_name'])\n",
            encoding="utf-8",
        )
        registry = AgentHookRegistry()
        registry.register(
            AgentHookEvent.PRE_TOOL_USE,
            CommandHookDefinition(command=["python", str(script)]),
        )
        executor = AgentHookExecutor(registry, AgentHookExecutionContext(cwd=tmp_path))
        result = await executor.execute_event(
            AgentHookEvent.PRE_TOOL_USE,
            {"tool_name": "read_file"},
        )
        assert result.results[0].success is True
        assert result.results[0].output.strip() == "read_file"

    @pytest.mark.asyncio
    async def test_command_hook_does_not_expand_arguments_in_argv(self, tmp_path: Path) -> None:
        registry = AgentHookRegistry()
        registry.register(
            AgentHookEvent.PRE_TOOL_USE,
            CommandHookDefinition(command=["echo", "$ARGUMENTS"]),
        )
        executor = AgentHookExecutor(registry, AgentHookExecutionContext(cwd=tmp_path))
        result = await executor.execute_event(
            AgentHookEvent.PRE_TOOL_USE,
            {"tool_name": "read_file"},
        )
        assert result.results[0].success is True
        assert result.results[0].output.strip() == "$ARGUMENTS"

    @pytest.mark.asyncio
    async def test_prompt_hook_injects_arguments_into_llm_prompt(self) -> None:
        registry = AgentHookRegistry()
        registry.register(
            AgentHookEvent.USER_PROMPT_SUBMIT,
            PromptHookDefinition(prompt="Check: $ARGUMENTS", block_on_failure=False),
        )
        api_client = AsyncMock()
        api_client.complete_hook_prompt = AsyncMock(return_value='{"ok": true}')
        executor = AgentHookExecutor(
            registry,
            AgentHookExecutionContext(cwd=Path.cwd(), api_client=api_client),
        )
        payload = {"task_description": "hello"}
        await executor.execute_event(AgentHookEvent.USER_PROMPT_SUBMIT, payload)
        sent_prompt = api_client.complete_hook_prompt.await_args.kwargs["prompt"]
        assert "$ARGUMENTS" not in sent_prompt
        assert "hello" in sent_prompt


@pytest.mark.unit
class TestLoaderAdr002AndPolicy:
    def test_adr002_deferred_cc_event_warns_not_registered(self, caplog: pytest.LogCaptureFixture) -> None:
        registry = AgentHookRegistry()
        with caplog.at_level("WARNING"):
            load_hooks_from_json(
                {"hooks": {"ConfigChange": [{"type": "http", "url": "https://example.com/x"}]}},
                registry,
            )
        assert registry.get_hooks(AgentHookEvent.STOP) == []
        assert any("ADR-002" in record.message for record in caplog.records)

    def test_pascal_case_cc_shape_maps_to_canonical(self) -> None:
        event = normalize_event_key("PreToolUse", options=HookLoadOptions())
        assert event == AgentHookEvent.PRE_TOOL_USE

    def test_policy_locked_prepends_paths(self, mock_agent, plugin_agent_config) -> None:
        from aiecs.domain.agent.plugins.defaults import derive_plugin_configs
        from aiecs.domain.agent.plugins.schema.manifest import PluginManifest

        manifest = PluginManifest(name="pack", hooks="./team.json")
        config = plugin_agent_config.model_copy(
            update={
                "policy_plugins": [
                    PluginConfig(
                        name="hook",
                        enabled=True,
                        policy_locked=True,
                        options={"paths": ["/policy/org.json"]},
                    )
                ],
                "plugins": [
                    PluginConfig(
                        name="hook",
                        enabled=False,
                        options={"paths": ["/agent/local.json"]},
                    )
                ],
            },
        )
        merged, _ = derive_plugin_configs(
            config,
            mock_agent,
            manifests=[manifest],
            manifest_dirs={"pack": Path("/tmp/pack")},
        )
        hook = next(plugin for plugin in merged if plugin.name == "hook")
        assert hook.enabled is True
        assert hook.options["paths"][0] == str(Path("/policy/org.json").resolve())


@pytest.mark.unit
class TestDisabledAndRegression:
    @pytest.mark.asyncio
    async def test_disabled_hook_no_registry_at_init(self, mock_agent) -> None:
        from aiecs.domain.agent.plugins.builtin.hook_plugin import HookPlugin
        from aiecs.domain.agent.plugins.context import AgentPluginContext

        plugin = HookPlugin(PluginConfig(name="hook", enabled=False), mock_agent)
        ctx = AgentPluginContext(agent=mock_agent, task={}, context={}, task_description="t")
        await plugin.on_agent_init(ctx)
        assert plugin.registry is None

    @pytest.mark.asyncio
    async def test_hook_baseline_parity_fixture(self) -> None:
        case = load_parity_fixture(_FIXTURES / "hook_baseline.yaml")
        got = await capture_parity_case(case)
        mismatches = compare_parity_expect(case.expect, got)
        assert mismatches == [], f"mismatch in {mismatches}"

    @pytest.mark.asyncio
    async def test_hook_disabled_matches_hybrid_baseline(self) -> None:
        baseline = load_parity_fixture(_FIXTURES / "hybrid_baseline.yaml")
        disabled_spec = dict(baseline.spec)
        disabled_spec["name"] = "hybrid_hook_disabled"
        plugins = list((disabled_spec.get("config") or {}).get("plugins") or [])
        plugins.append(PluginConfig(name="hook", enabled=False).model_dump())
        disabled_spec["config"] = {**(disabled_spec.get("config") or {}), "plugins": plugins}
        disabled_case = ParityCase(
            path=_FIXTURES / "hybrid_baseline.yaml",
            name="hybrid_hook_disabled",
            spec=disabled_spec,
        )

        baseline_got = await capture_parity_case(baseline)
        disabled_got = await capture_parity_case(disabled_case)
        assert disabled_got.messages_normalized == baseline_got.messages_normalized
        assert disabled_got.tool_schema_names == baseline_got.tool_schema_names
        assert disabled_got.execute_task_response == baseline_got.execute_task_response


class _StubTool(BaseTool):
    async def run_async(self, **kwargs):
        return {"status": "ok"}


class _FCClient(BaseLLMClient):
    def __init__(self) -> None:
        super().__init__(provider_name="openai")

    async def generate_text(self, messages, **kwargs) -> LLMResponse:
        resp = LLMResponse(content="run tool", provider="openai", model="m", tokens_used=1)
        resp.tool_calls = [
            {
                "id": "call_fc",
                "type": "function",
                "function": {"name": "parity_search", "arguments": '{"query": "hooks"}'},
            }
        ]
        return resp

    async def stream_text(self, *args, **kwargs):
        yield "run tool"

    async def close(self) -> None:
        return None


@pytest.mark.unit
class TestToolAgentHookWiring:
    @pytest.mark.asyncio
    async def test_fc_mode_calls_dispatch_tool_with_hooks(self) -> None:
        dispatch_spy = AsyncMock(
            return_value=type(
                "R",
                (),
                {
                    "blocked": False,
                    "error_message": None,
                    "tool_output": {"status": "ok"},
                    "tool_content": '{"status": "ok"}',
                    "block_reason": "",
                },
            )()
        )
        agent = ToolAgent(
            agent_id="fc-hook",
            name="FC Hook",
            llm_client=_FCClient(),
            tools={"parity_search": _StubTool(tool_name="parity_search")},
            config=AgentConfiguration(llm_model="m"),
        )
        await agent.initialize()

        with patch(
            "aiecs.domain.agent.plugins.hooks.tool_dispatch.dispatch_tool_with_hooks",
            dispatch_spy,
        ):
            result = await agent.execute_task({"description": "search parity topic"}, {})

        assert result["success"] is True
        dispatch_spy.assert_awaited()
        kwargs = dispatch_spy.await_args.kwargs
        assert kwargs["offload"] is False
        assert kwargs["tool_name"] == "parity_search"

    @pytest.mark.asyncio
    async def test_direct_mode_calls_dispatch_tool_with_hooks(self) -> None:
        dispatch_spy = AsyncMock(
            return_value=type(
                "R",
                (),
                {
                    "blocked": False,
                    "error_message": None,
                    "tool_output": {"status": "ok"},
                    "tool_content": '{"status": "ok"}',
                    "block_reason": "",
                },
            )()
        )
        agent = ToolAgent(
            agent_id="direct-hook",
            name="Direct Hook",
            tools={"parity_search": _StubTool(tool_name="parity_search")},
            config=AgentConfiguration(llm_model="m"),
        )
        await agent.initialize()

        with patch(
            "aiecs.domain.agent.plugins.hooks.tool_dispatch.dispatch_tool_with_hooks",
            dispatch_spy,
        ):
            result = await agent.execute_task(
                {
                    "description": "direct",
                    "tool": "parity_search",
                    "operation": "run",
                    "parameters": {},
                },
                {},
            )

        assert result["success"] is True
        dispatch_spy.assert_awaited_once()
        assert dispatch_spy.await_args.kwargs["offload"] is False


@pytest.mark.unit
class TestVerifyOpenHarnessRefs:
    def test_verify_openharness_refs_script_passes(self) -> None:
        import subprocess

        script = (
            Path(__file__).resolve().parents[6]
            / "issue_report"
            / "agent"
            / "reference"
            / "verify_openharness_refs.sh"
        )
        proc = subprocess.run(["bash", str(script)], capture_output=True, text=True, check=False)
        assert proc.returncode == 0, proc.stderr or proc.stdout
