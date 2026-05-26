# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Capture HybridAgent parity baselines from fixture specs (P2-00, P2-15).

Run before plugin integration changes to refresh golden YAML under tests/fixtures/plugin_parity/.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from collections.abc import AsyncGenerator
from typing import Any

import yaml

from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.models import PluginPhase
from aiecs.domain.agent.plugins.testing.normalize import (
    normalize_execute_task_response,
    normalize_messages,
    normalize_plugin_state_keys,
    normalize_tool_schema_names,
)
from aiecs.domain.agent.skills.models import SkillDefinition, SkillMetadata, SkillResource
from aiecs.domain.agent.skills.registry import SkillRegistry
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse
from aiecs.tools.base_tool import BaseTool


class ParityStubTool(BaseTool):
    """Minimal in-process tool so schema generation succeeds in CI (no registry I/O)."""

    async def run_async(self, op: str, **kwargs: Any) -> Any:
        return {"status": "ok", "operation": op}


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
    """OpenAI-provider mock for HybridAgent tool-loop parity capture."""

    def __init__(self, final_output: str = "Parity baseline final response."):
        super().__init__(provider_name="openai")
        self._final_output = final_output

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
        return LLMResponse(
            content=self._final_output,
            provider="openai",
            model=model or "parity-mock",
            tokens_used=42,
        )

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
            for token in self._final_output.split():
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


async def create_agent_from_spec(spec: dict[str, Any]) -> tuple[HybridAgent, dict[str, Any], dict[str, Any], str]:
    """Build and initialize a HybridAgent from a fixture spec."""
    config = _build_config(spec)
    tools = _resolve_tools(spec)
    task = spec.get("task") or {"description": "Parity test task"}
    context = dict(spec.get("context") or {})
    task_description = str(task.get("description") or task.get("prompt") or task.get("task", ""))

    llm_cfg = spec.get("capture") or {}
    client = ParityMockLLMClient(final_output=llm_cfg.get("mock_final_output", "Parity baseline final response."))

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

    await agent.initialize()
    return agent, task, context, task_description


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
        return [], normalize_execute_task_response(result)

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
    agent, task, context, task_description = await create_agent_from_spec(spec)

    streaming_seq = await capture_streaming_phase_sequence(agent, task, context)

    agent2, task2, context2, _ = await create_agent_from_spec(spec)
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


async def capture_fixture_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Run HybridAgent and return normalized expect block for a fixture spec."""
    mode = spec.get("parity_mode")
    if mode == "streaming_phases":
        return await capture_streaming_phases_spec(spec)

    agent, task, context, task_description = await create_agent_from_spec(spec)

    plugin_ctx = agent._make_plugin_context(
        task=task,
        context=context,
        task_description=task_description,
    )
    messages = await agent._build_initial_messages_async(task_description, context, plugin_ctx)
    tool_schema_names = normalize_tool_schema_names(agent._tool_schemas)

    execute_result = await agent.execute_task(task, context)
    execute_shell = normalize_execute_task_response(execute_result)

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


async def refresh_all(fixtures_dir: Path) -> None:
    for path in sorted(fixtures_dir.glob("hybrid_*.yaml")):
        await refresh_fixture(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh plugin parity golden fixtures (P2-00).")
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=Path("tests/fixtures/plugin_parity"),
        help="Directory containing hybrid_*.yaml fixtures",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        help="Refresh a single fixture file",
    )
    args = parser.parse_args()
    if args.fixture:
        asyncio.run(refresh_fixture(args.fixture))
    else:
        asyncio.run(refresh_all(args.fixtures_dir))


if __name__ == "__main__":
    main()
