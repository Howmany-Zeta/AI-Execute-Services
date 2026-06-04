# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Capture agent parity baselines from fixture specs (P2-00, P3-00).

Run before plugin integration changes to refresh golden YAML under
``tests/fixtures/plugin_parity/``.

Regenerate all Hybrid fixtures::

    poetry run python -m aiecs.domain.agent.plugins.testing.capture

Regenerate LLM/Tool fixtures (P3-00)::

    poetry run python -m aiecs.domain.agent.plugins.testing.capture \\
        --pattern 'llm_*.yaml' --pattern 'tool_*.yaml'

Single fixture::

    poetry run python -m aiecs.domain.agent.plugins.testing.capture \\
        --fixture tests/fixtures/plugin_parity/llm_memory_multiturn.yaml
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from collections.abc import AsyncGenerator
from typing import Any, Union
from unittest.mock import AsyncMock

import yaml

from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.llm_agent import LLMAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.builtin.knowledge_plugin import effective_task_description
from aiecs.domain.agent.plugins.models import PluginConfig, PluginPhase
from aiecs.domain.agent.plugins.testing.normalize import (
    normalize_execute_task_response,
    normalize_messages,
    normalize_plugin_state_keys,
    normalize_tool_schema_names,
)
from aiecs.domain.agent.skills.models import SkillDefinition, SkillMetadata, SkillResource
from aiecs.domain.agent.skills.registry import SkillRegistry
from aiecs.domain.agent.tool_agent import ToolAgent
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse
from aiecs.tools.base_tool import BaseTool

ParityAgent = Union[HybridAgent, LLMAgent, ToolAgent]


class _ParityGraphStore:
    """Minimal non-NoOp graph backend so KnowledgePlugin parity hooks stay active."""

    async def initialize(self) -> None:
        return None

    async def close(self) -> None:
        return None


class ParityStubTool(BaseTool):
    """Minimal in-process tool so schema generation succeeds in CI (no registry I/O)."""

    async def run_async(self, op: str = "run", **kwargs: Any) -> Any:
        return {"status": "ok", "operation": op, **kwargs}


def _agent_type(spec: dict[str, Any]) -> str:
    return str((spec.get("agent") or {}).get("type") or "HybridAgent")


def _resolve_tools(spec: dict[str, Any]) -> list[str] | dict[str, BaseTool]:
    """Map fixture tool names to instances when registry tools are unavailable."""
    raw = spec.get("agent", {}).get("tools", ["parity_search"])
    if isinstance(raw, dict):
        return raw
    instances: dict[str, BaseTool] = {}
    names: list[str] = []
    for name in raw:
        if name in ("parity_search", "search"):
            key = "parity_search"
            if key not in instances:
                instances[key] = ParityStubTool(tool_name=key)
            names.append(key)
        else:
            names.append(name)
    if instances:
        return instances
    return names


class ParityMockLLMClient(BaseLLMClient):
    """OpenAI-provider mock for agent parity capture (Hybrid tool loop, LLM, Tool FC)."""

    def __init__(
        self,
        final_output: str | list[str] = "Parity baseline final response.",
        *,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_calls_per_call: list[list[dict[str, Any]] | None] | None = None,
    ):
        super().__init__(provider_name="openai")
        self._outputs = final_output if isinstance(final_output, list) else [final_output]
        self._call_index = 0
        self._static_tool_calls = tool_calls
        self._tool_calls_per_call = tool_calls_per_call

    def _next_output(self) -> str:
        idx = min(self._call_index, len(self._outputs) - 1)
        self._call_index += 1
        return self._outputs[idx]

    def _tool_calls_for_call(self) -> list[dict[str, Any]] | None:
        if self._tool_calls_per_call is not None:
            idx = self._call_index - 1
            if 0 <= idx < len(self._tool_calls_per_call):
                return self._tool_calls_per_call[idx]
            return None
        return self._static_tool_calls

    async def generate_text(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        context: dict[str, Any] | None = None,
        *,
        input_price: float | None = None,
        output_price: float | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        content = self._next_output()
        response = LLMResponse(
            content=content,
            provider="openai",
            model=model or "parity-mock",
            tokens_used=42,
        )
        tool_calls = self._tool_calls_for_call()
        if tool_calls:
            setattr(response, "tool_calls", tool_calls)
        return response

    def stream_text(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        context: dict[str, Any] | None = None,
        *,
        input_price: float | None = None,
        output_price: float | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        async def _gen() -> AsyncGenerator[str, None]:
            for token in self._next_output().split():
                yield token

        return _gen()

    async def close(self) -> None:
        pass


def _parity_skill() -> SkillDefinition:
    metadata = SkillMetadata(
        name="parity-test-skill",
        description="Minimal skill for plugin parity baseline",
        version="1.0.0",
        tags=["parity"],
    )
    return SkillDefinition(
        metadata=metadata,
        skill_path=Path("/parity/test-skill"),
        scripts={
            "run": SkillResource(
                path="scripts/run.py",
                type="script",
                executable=True,
                mode="native",
                description="Run parity skill",
            )
        },
    )


def _build_config(spec: dict[str, Any]) -> AgentConfiguration:
    raw = dict(spec.get("config") or {})
    raw.setdefault("goal", "Plugin parity test agent")
    raw.setdefault("llm_model", "parity-mock")
    raw.setdefault("enable_prompt_caching", False)
    return AgentConfiguration(**raw)


def _build_mock_client(spec: dict[str, Any]) -> ParityMockLLMClient | None:
    capture = spec.get("capture") or {}
    if capture.get("no_llm_client"):
        return None

    outputs: list[str] = []
    warmup = capture.get("warmup")
    if warmup:
        outputs.append(str(warmup.get("mock_output", "Warmup parity response.")))
    outputs.append(str(capture.get("mock_final_output", "Parity baseline final response.")))

    tool_calls = capture.get("mock_tool_calls")
    tool_calls_per_call = capture.get("mock_tool_calls_per_call")
    if tool_calls_per_call is not None and not isinstance(tool_calls_per_call, list):
        tool_calls_per_call = None

    if len(outputs) == 1:
        return ParityMockLLMClient(
            final_output=outputs[0],
            tool_calls=tool_calls,
            tool_calls_per_call=tool_calls_per_call,
        )
    return ParityMockLLMClient(
        final_output=outputs,
        tool_calls=tool_calls,
        tool_calls_per_call=tool_calls_per_call,
    )


async def create_hybrid_agent_from_spec(
    spec: dict[str, Any],
) -> tuple[HybridAgent, dict[str, Any], dict[str, Any], str]:
    """Build and initialize a HybridAgent from a fixture spec."""
    raw_config = dict(spec.get("config") or {})
    if _spec_uses_knowledge_plugin(spec) and not raw_config.get("plugins"):
        raw_config["plugins"] = [PluginConfig(name="knowledge", enabled=True)]
    spec_with_config = dict(spec)
    spec_with_config["config"] = raw_config
    config = _build_config(spec_with_config)
    tools = _resolve_tools(spec)
    task = spec.get("task") or {"description": "Parity test task"}
    context = dict(spec.get("context") or {})
    task_description = str(task.get("description") or task.get("prompt") or task.get("task", ""))

    llm_cfg = spec.get("capture") or {}
    client = _build_mock_client(spec)
    assert client is not None

    skill_registry = None
    if config.skills_enabled:
        skill_registry = SkillRegistry()
        parity_skill = _parity_skill()
        if skill_registry.get_skill(parity_skill.metadata.name) is None:
            skill_registry.register_skill(parity_skill)

    agent = HybridAgent(
        agent_id="plugin-parity-capture",
        name="Plugin Parity Capture",
        llm_client=client,
        tools=tools,
        config=config,
        max_iterations=llm_cfg.get("max_iterations", 3),
    )
    if skill_registry is not None:
        agent._skill_registry = skill_registry

    if _spec_uses_knowledge_plugin(spec):
        await _apply_knowledge_parity_extras(agent, spec)

    await agent.initialize()
    return agent, task, context, task_description


async def create_llm_agent_from_spec(
    spec: dict[str, Any],
) -> tuple[LLMAgent, dict[str, Any], dict[str, Any], str]:
    """Build and initialize an LLMAgent from a fixture spec."""
    config = _build_config(spec)
    task = spec.get("task") or {"description": "Parity test task"}
    context = dict(spec.get("context") or {})
    task_description = str(task.get("description") or task.get("prompt") or task.get("task", ""))

    client = _build_mock_client(spec)
    assert client is not None

    agent = LLMAgent(
        agent_id="plugin-parity-llm-capture",
        name="Plugin Parity LLM Capture",
        llm_client=client,
        config=config,
    )
    await agent.initialize()

    capture = spec.get("capture") or {}
    warmup = capture.get("warmup")
    if warmup:
        warmup_task = dict(warmup.get("task") or {})
        if not warmup_task.get("description"):
            warmup_task["description"] = "Warmup turn"
        await agent.execute_task(warmup_task, dict(warmup.get("context") or {}))

    return agent, task, context, task_description


async def create_tool_agent_from_spec(
    spec: dict[str, Any],
) -> tuple[ToolAgent, dict[str, Any], dict[str, Any], str]:
    """Build and initialize a ToolAgent from a fixture spec."""
    config = _build_config(spec)
    tools = _resolve_tools(spec)
    task = spec.get("task") or {"description": "Parity test task"}
    context = dict(spec.get("context") or {})
    task_description = str(task.get("description") or task.get("prompt") or task.get("task", ""))

    client = _build_mock_client(spec)

    agent = ToolAgent(
        agent_id="plugin-parity-tool-capture",
        name="Plugin Parity Tool Capture",
        llm_client=client,
        tools=tools,
        config=config,
    )
    await agent.initialize()
    return agent, task, context, task_description


async def _build_graph_store(spec: dict[str, Any]) -> Any:
    """In-process graph store stub for knowledge parity fixtures (no external I/O)."""
    capture = spec.get("capture") or {}
    if capture.get("no_graph_store"):
        return None
    store = _ParityGraphStore()
    await store.initialize()
    return store


def _spec_uses_knowledge_plugin(spec: dict[str, Any]) -> bool:
    agent_type = _agent_type(spec)
    if agent_type == "HybridAgent" and str(spec.get("name", "")).startswith("knowledge_"):
        return True
    config = spec.get("config") or {}
    plugins = config.get("plugins") or []
    for entry in plugins:
        if isinstance(entry, dict) and entry.get("name") == "knowledge" and entry.get("enabled", True):
            return True
        if getattr(entry, "name", None) == "knowledge" and getattr(entry, "enabled", True):
            return True
    return False


async def _apply_knowledge_parity_extras(agent: HybridAgent, spec: dict[str, Any]) -> None:
    """Wire graph store, cached context, and mocked reasoning for knowledge parity."""
    capture = spec.get("capture") or {}
    agent_cfg = spec.get("agent") or {}
    graph_store = await _build_graph_store(spec)
    if graph_store is not None:
        agent.graph_store = graph_store
        agent.enable_graph_reasoning = agent_cfg.get("enable_graph_reasoning", True)

    knowledge_context = capture.get("knowledge_context") or {}
    if isinstance(knowledge_context, dict):
        agent._knowledge_context = {str(query): dict(entry) for query, entry in knowledge_context.items() if isinstance(entry, dict)}

    mock_graph_result = capture.get("mock_graph_result")
    if isinstance(mock_graph_result, dict) and graph_store is not None:
        graph_store.reason = AsyncMock(return_value=dict(mock_graph_result))


async def create_agent_from_spec(
    spec: dict[str, Any],
) -> tuple[ParityAgent, dict[str, Any], dict[str, Any], str]:
    """Build and initialize an agent from a fixture spec (Hybrid default)."""
    agent_type = _agent_type(spec)
    if agent_type == "LLMAgent":
        return await create_llm_agent_from_spec(spec)
    if agent_type == "ToolAgent":
        return await create_tool_agent_from_spec(spec)
    return await create_hybrid_agent_from_spec(spec)


def _shell_extra_fields(spec: dict[str, Any]) -> frozenset[str]:
    agent_type = _agent_type(spec)
    if agent_type == "ToolAgent":
        task = spec.get("task") or {}
        if task.get("tool"):
            return frozenset({"tool_used", "operation"})
        return frozenset({"tool_calls_count"})
    if _spec_uses_knowledge_plugin(spec) and (spec.get("capture") or {}).get("mock_graph_result"):
        return frozenset({"source", "confidence", "evidence_count"})
    return frozenset()


def normalize_phase_sequence(
    entries: list[tuple[str, int]] | list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Stable ``plugin_phase_started`` sequence for golden comparison."""
    out: list[dict[str, Any]] = []
    for entry in entries:
        if isinstance(entry, dict):
            out.append(
                {
                    "phase": str(entry["phase"]),
                    "plugin_count": int(entry["plugin_count"]),
                }
            )
        else:
            phase, count = entry
            out.append({"phase": str(phase), "plugin_count": int(count)})
    return out


async def capture_sync_phase_sequence(
    agent: HybridAgent,
    task: dict[str, Any],
    context: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Record ``run_phase`` order during ``execute_task`` (§12.1 streaming parity)."""
    manager = agent._plugin_manager
    if manager is None:
        result = await agent.execute_task(task, context)
        return [], normalize_execute_task_response(result, extra_fields=_shell_extra_fields({}))

    order: list[tuple[str, int]] = []
    original_run_phase = manager.run_phase

    async def tracking_run_phase(phase: PluginPhase, **kwargs: Any) -> Any:
        plugins = manager._plugins_for_phase(phase)
        order.append((phase.value, len(plugins)))
        return await original_run_phase(phase, **kwargs)

    manager.run_phase = tracking_run_phase  # type: ignore[method-assign]
    result = await agent.execute_task(task, context)
    return normalize_phase_sequence(order), normalize_execute_task_response(result)


async def capture_streaming_phase_sequence(
    agent: HybridAgent,
    task: dict[str, Any],
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Collect ``plugin_phase_started`` events from ``execute_task_streaming``."""
    order: list[tuple[str, int]] = []
    async for event in agent.execute_task_streaming(task, context):
        if event.get("type") == "plugin_phase_started":
            order.append((event.get("phase", ""), int(event.get("plugin_count", 0))))
    return normalize_phase_sequence(order)


async def capture_streaming_phases_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Capture sync vs streaming plugin phase order (``hybrid_streaming_phases``)."""
    agent, task, context, task_description = await create_hybrid_agent_from_spec(spec)

    streaming_seq = await capture_streaming_phase_sequence(agent, task, context)

    agent2, task2, context2, _ = await create_hybrid_agent_from_spec(spec)
    sync_seq, execute_shell = await capture_sync_phase_sequence(agent2, task2, context2)

    plugin_ctx = agent2._make_plugin_context(
        task=task2,
        context=context2,
        task_description=task_description,
    )
    messages = await agent2._build_initial_messages_async(task_description, context2, plugin_ctx)

    return {
        "streaming_phase_sequence": streaming_seq,
        "sync_phase_sequence": sync_seq,
        "messages_normalized": normalize_messages(messages),
        "tool_schema_names": normalize_tool_schema_names(agent2._tool_schemas),
        "plugin_state_keys": [],
        "execute_task_response": execute_shell,
    }


async def capture_llm_tool_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Capture LLMAgent / ToolAgent parity via plugin-aware execute_task (P3-00+)."""
    agent, task, context, task_description = await create_agent_from_spec(spec)
    capture_cfg = spec.get("capture") or {}
    agent_type = _agent_type(spec)
    extra = _shell_extra_fields(spec)
    capture_messages = capture_cfg.get("capture_messages", True)

    messages_normalized: list[dict[str, Any]] = []
    tool_schema_names: list[str] = []

    if capture_messages and agent_type == "LLMAgent":
        assert isinstance(agent, LLMAgent)
        plugin_ctx = agent._make_plugin_context(
            task=task,
            context=context,
            task_description=task_description,
        )
        agent._apply_task_plugin_configs(task=task, context=context)
        if agent._plugin_manager is not None:
            await agent._plugin_manager.run_phase(PluginPhase.PRE_TASK, ctx=plugin_ctx)
        if agent._should_use_legacy_messages(task, context):
            messages = agent._build_messages(task_description, context)
        else:
            messages = await agent._build_messages_via_plugins(
                task_description,
                context,
                plugin_ctx,
            )
        messages_normalized = normalize_messages(messages)
    elif capture_messages and agent_type == "ToolAgent":
        assert isinstance(agent, ToolAgent)
        task_desc = task.get("description") or task.get("prompt") or task.get("task")
        if task_desc and agent.llm_client is not None:
            plugin_ctx = agent._make_plugin_context(
                task=task,
                context=context,
                task_description=task_description,
            )
            agent._apply_task_plugin_configs(task=task, context=context)
            if agent._plugin_manager is not None:
                await agent._plugin_manager.run_phase(PluginPhase.PRE_TASK, ctx=plugin_ctx)
                await agent._plugin_manager.run_phase(
                    PluginPhase.PRE_MAIN_LOOP,
                    ctx=plugin_ctx,
                )
            if agent._should_use_legacy_messages(task, context):
                messages = agent._build_messages(str(task_desc), context)
            else:
                messages = await agent._build_messages_via_plugins(
                    str(task_desc),
                    context,
                    plugin_ctx,
                )
            messages_normalized = normalize_messages(messages)
            tool_schema_names = normalize_tool_schema_names(agent._tool_schemas)

    execute_result = await agent.execute_task(task, context)
    execute_shell = normalize_execute_task_response(execute_result, extra_fields=extra)

    result: dict[str, Any] = {
        "execute_task_response": execute_shell,
    }
    if capture_messages:
        result["messages_normalized"] = messages_normalized
        result["tool_schema_names"] = tool_schema_names
    if agent_type == "HybridAgent":
        result["plugin_state_keys"] = []
    return result


async def capture_fixture_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Run agent and return normalized expect block for a fixture spec."""
    mode = spec.get("parity_mode")
    if mode == "streaming_phases":
        return await capture_streaming_phases_spec(spec)

    agent_type = _agent_type(spec)
    if agent_type in ("LLMAgent", "ToolAgent"):
        return await capture_llm_tool_spec(spec)

    agent, task, context, task_description = await create_hybrid_agent_from_spec(spec)
    extra = _shell_extra_fields(spec)

    plugin_ctx = agent._make_plugin_context(
        task=task,
        context=context,
        task_description=task_description,
    )
    agent._apply_task_plugin_configs(task=task, context=context)
    if agent._plugin_manager is not None:
        await agent._plugin_manager.run_phase(PluginPhase.PRE_TASK, ctx=plugin_ctx)

    build_task = effective_task_description(plugin_ctx, task_description) if _spec_uses_knowledge_plugin(spec) else task_description
    messages = await agent._build_initial_messages_async(build_task, context, plugin_ctx)
    tool_schema_names = normalize_tool_schema_names(agent._tool_schemas)

    execute_result = await agent.execute_task(task, context)
    execute_shell = normalize_execute_task_response(execute_result, extra_fields=extra)

    plugin_state_keys: list[str] = []
    if plugin_ctx.plugin_state:
        plugin_state_keys = normalize_plugin_state_keys(plugin_ctx.plugin_state)

    return {
        "messages_normalized": normalize_messages(messages),
        "tool_schema_names": tool_schema_names,
        "plugin_state_keys": plugin_state_keys,
        "execute_task_response": execute_shell,
    }


def load_fixture(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected mapping at root")
    return data


def write_fixture(path: Path, spec: dict[str, Any], expect: dict[str, Any]) -> None:
    out = dict(spec)
    out["expect"] = expect
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(out, handle, sort_keys=False, allow_unicode=True, default_flow_style=False)


async def refresh_fixture(path: Path) -> None:
    spec = load_fixture(path)
    expect = await capture_fixture_spec(spec)
    write_fixture(path, {k: v for k, v in spec.items() if k != "expect"}, expect)
    print(f"Updated {path}")


async def refresh_all(fixtures_dir: Path, patterns: list[str] | None = None) -> None:
    globs = patterns or ["hybrid_*.yaml"]
    seen: set[Path] = set()
    for pattern in globs:
        for path in sorted(fixtures_dir.glob(pattern)):
            if path in seen:
                continue
            seen.add(path)
            await refresh_fixture(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh plugin parity golden fixtures (P2-00 / P3-00).")
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=Path("tests/fixtures/plugin_parity"),
        help="Directory containing parity YAML fixtures",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        help="Refresh a single fixture file",
    )
    parser.add_argument(
        "--pattern",
        action="append",
        dest="patterns",
        help="Glob pattern(s) under fixtures-dir (default: hybrid_*.yaml)",
    )
    args = parser.parse_args()
    if args.fixture:
        asyncio.run(refresh_fixture(args.fixture))
    else:
        asyncio.run(refresh_all(args.fixtures_dir, args.patterns))


if __name__ == "__main__":
    main()
