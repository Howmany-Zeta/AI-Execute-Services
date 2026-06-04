# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
KnowledgePlugin — knowledge graph retrieval and augmentation (§4.3, §4.6).

PRE_TASK augmentation writes ``plugin_state["knowledge.augmented_task"]`` (§4.3).
PRE_MAIN_LOOP may return ``PluginShortCircuitResult`` for high-confidence graph hits (§4.4).
``ON_ITERATION_START`` writes ``plugin_state["knowledge.iteration_context"]``; HybridAgent
appends it to ``messages`` before each tool-loop iteration (§4.3).
HybridAgent reads augmented task after PRE_TASK and before BUILD_MESSAGES; ``ctx.task_description``
is left unchanged.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar

from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext, PluginShortCircuitResult
from aiecs.infrastructure.knowledge import NoOpGraphStore, create_graph_store
from aiecs.domain.agent.plugins.identifier import format_plugin_id
from aiecs.domain.agent.plugins.models import PluginMetadata
from aiecs.llm import LLMMessage

logger = logging.getLogger(__name__)

PLUGIN_STATE_AUGMENTED_TASK_KEY = "knowledge.augmented_task"
PLUGIN_STATE_ITERATION_CONTEXT_KEY = "knowledge.iteration_context"
RETRIEVED_KNOWLEDGE_HEADER = "RETRIEVED KNOWLEDGE:"
PLUGIN_ID = format_plugin_id("knowledge", "builtin")
GRAPH_SHORT_CIRCUIT_KEYWORDS = (
    "connected",
    "connection",
    "relationship",
    "knows",
    "works at",
)
GRAPH_SHORT_CIRCUIT_CONFIDENCE_THRESHOLD = 0.7
DEFAULT_SEARCH_LIMIT = 10


def effective_task_description(plugin_ctx: AgentPluginContext, fallback: str) -> str:
    """Task string for BUILD_MESSAGES after PRE_TASK (§4.3)."""
    augmented = plugin_ctx.plugin_state.get(PLUGIN_STATE_AUGMENTED_TASK_KEY)
    if isinstance(augmented, str) and augmented:
        return augmented
    return fallback


def _graph_store_ready(agent: Any) -> tuple[Any | None, bool]:
    """Return (graph_store, active) when store is non-NoOp and reasoning is enabled."""
    graph_store = getattr(agent, "graph_store", None)
    enable_graph_reasoning = getattr(agent, "enable_graph_reasoning", True)
    if graph_store is None or isinstance(graph_store, NoOpGraphStore) or not enable_graph_reasoning:
        return graph_store, False
    return graph_store, True


async def _call_graph_store_method(
    graph_store: Any,
    method_name: str,
    *args: Any,
    **kwargs: Any,
) -> Any | None:
    """Invoke an optional async/sync method on the L2 graph store backend."""
    method = getattr(graph_store, method_name, None)
    if not callable(method):
        return None
    result = method(*args, **kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


async def augment_prompt_with_knowledge(
    agent: Any,
    task: str,
    context: dict[str, Any] | None = None,
) -> str:
    """Augment a task with agent-local cached knowledge context (optional app hook)."""
    _ = context
    _, active = _graph_store_ready(agent)
    if not active:
        return task

    knowledge_context = getattr(agent, "_knowledge_context", None)
    if not isinstance(knowledge_context, dict):
        return task

    relevant_knowledge: list[dict[str, Any]] = []
    for query, kg_context in knowledge_context.items():
        if any(word in task.lower() for word in query.lower().split()):
            relevant_knowledge.append(
                {
                    "query": query,
                    "answer": kg_context["answer"],
                    "confidence": kg_context.get("confidence", 0.0),
                    "timestamp": kg_context.get("timestamp"),
                }
            )

    if not relevant_knowledge:
        return task

    knowledge_items = [(_KnowledgeCacheItem(item), item["confidence"]) for item in relevant_knowledge]
    prioritized = sorted(knowledge_items, key=lambda pair: pair[1], reverse=True)

    formatted_knowledge = []
    for kg_item, _priority_score in prioritized[:3]:
        d = kg_item.data
        formatted_knowledge.append(f"- {d['query']}: {d['answer']} (confidence: {d['confidence']:.2f})")

    knowledge_section = "\n\nRELEVANT KNOWLEDGE FROM GRAPH:\n" + "\n".join(formatted_knowledge)
    return task + knowledge_section


class _KnowledgeCacheItem:
    """Cache entry wrapper for task augmentation prioritization."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.created_at = None
        timestamp = data.get("timestamp")
        if timestamp:
            try:
                from dateutil import parser

                self.created_at = parser.parse(timestamp)
            except Exception:
                pass


def is_graph_short_circuit_query(task_description: str) -> bool:
    """True when the task matches graph-reasoning keyword heuristics."""
    task_lower = task_description.lower()
    return any(keyword in task_lower for keyword in GRAPH_SHORT_CIRCUIT_KEYWORDS)


def short_circuit_result_from_graph(graph_result: dict[str, Any]) -> dict[str, Any] | None:
    """Build execute_task kernel dict from graph reasoning output (§4.4)."""
    if "answer" not in graph_result:
        return None
    confidence = graph_result.get("confidence", 0)
    if confidence <= GRAPH_SHORT_CIRCUIT_CONFIDENCE_THRESHOLD:
        return None
    return {
        "success": True,
        "output": graph_result["answer"],
        "confidence": confidence,
        "source": "knowledge_graph",
        "evidence_count": graph_result.get("evidence_count", 0),
        "reasoning_trace": graph_result.get("reasoning_trace", []),
    }


async def try_knowledge_graph_short_circuit(
    agent: Any,
    task_description: str,
    context: dict[str, Any],
    *,
    query: str | None = None,
) -> PluginShortCircuitResult | None:
    """
    Attempt PRE_MAIN_LOOP short-circuit via high-confidence graph reasoning (§4.4).

    Uses ``graph_store.reason(...)`` when the private L2 backend provides it.
    """
    graph_store, active = _graph_store_ready(agent)
    if not active:
        return None
    if not is_graph_short_circuit_query(task_description):
        return None

    graph_result = await _call_graph_store_method(
        graph_store,
        "reason",
        query or task_description,
        context=context,
    )
    if not isinstance(graph_result, dict):
        return None

    kernel = short_circuit_result_from_graph(graph_result)
    if kernel is None:
        return None

    logger.info(
        "KnowledgePlugin short-circuit for agent %s (confidence=%s)",
        getattr(agent, "agent_id", "?"),
        kernel.get("confidence"),
    )
    return PluginShortCircuitResult(
        result=kernel,
        source_plugin_id=PLUGIN_ID,
        reason="knowledge_graph_short_circuit",
    )


def format_retrieved_knowledge_entities(entities: list[Any]) -> str:
    """Format retrieved entities for prompt injection."""
    lines: list[str] = []
    for entity in entities:
        entity_type = getattr(entity, "entity_type", type(entity).__name__)
        entity_id = getattr(entity, "id", str(entity))
        entity_str = f"- {entity_type}: {entity_id}"
        properties = getattr(entity, "properties", None)
        if properties:
            props_str = ", ".join(f"{key}={value}" for key, value in properties.items())
            entity_str += f" ({props_str})"
        lines.append(entity_str)
    return "\n".join(lines)


def _apply_knowledge_options_to_agent(agent: Any, options: dict[str, Any]) -> Any:
    """Context manager: temporarily apply plugin options to the agent for retrieval."""
    return _KnowledgeOptionsScope(agent, options)


class _KnowledgeOptionsScope:
    def __init__(self, agent: Any, options: dict[str, Any]) -> None:
        self._agent = agent
        self._options = options
        self._restore: list[tuple[str, Any]] = []

    def __enter__(self) -> None:
        max_context_size = self._options.get("max_context_size")
        if max_context_size is not None and hasattr(self._agent, "_max_context_size"):
            self._restore.append(("_max_context_size", self._agent._max_context_size))
            self._agent._max_context_size = int(max_context_size)

        if self._options.get("enable_knowledge_caching") is False and hasattr(self._agent, "_graph_cache"):
            self._restore.append(("_graph_cache", self._agent._graph_cache))
            self._agent._graph_cache = None

    def __exit__(self, *_exc: object) -> None:
        for attr, value in reversed(self._restore):
            setattr(self._agent, attr, value)


async def retrieve_iteration_knowledge(
    agent: Any,
    task: str,
    context: dict[str, Any],
    iteration: int,
    *,
    options: dict[str, Any] | None = None,
    event_callback: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
) -> dict[str, Any] | None:
    """Retrieve knowledge for a tool-loop iteration via ``graph_store.search``."""
    _ = event_callback, context.get("_knowledge_event_callback") if context else None
    graph_store, active = _graph_store_ready(agent)
    if not active:
        return None

    plugin_options = options or {}
    limit = int(plugin_options.get("max_context_size", DEFAULT_SEARCH_LIMIT))

    with _apply_knowledge_options_to_agent(agent, plugin_options):
        entities = await _call_graph_store_method(graph_store, "search", task, limit=limit)
    if not isinstance(entities, list) or not entities:
        return None

    formatted = format_retrieved_knowledge_entities(entities)
    if not formatted:
        return None

    return {
        "iteration": iteration,
        "entity_count": len(entities),
        "formatted": formatted,
    }


def inject_iteration_knowledge_into_messages(
    messages: list[LLMMessage],
    plugin_ctx: AgentPluginContext,
) -> list[LLMMessage]:
    """Append iteration retrieval block to ``messages`` when plugin state is set."""
    block = plugin_ctx.plugin_state.get(PLUGIN_STATE_ITERATION_CONTEXT_KEY)
    if not isinstance(block, dict):
        return messages
    formatted = block.get("formatted")
    if not isinstance(formatted, str) or not formatted:
        return messages

    updated = list(messages)
    updated.append(
        LLMMessage(
            role="user",
            content=f"\n\n{RETRIEVED_KNOWLEDGE_HEADER}\n{formatted}",
        )
    )
    return updated


class KnowledgePlugin(BaseAgentPlugin):
    """Builtin knowledge plugin: task augmentation, graph short-circuit, iteration retrieval."""

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="knowledge",
        version="1.0.0",
        description="Knowledge graph retrieval and augmentation plugin",
        priority=40,
        default_enabled=False,
    )

    async def on_agent_init(self, ctx: AgentPluginContext) -> None:
        """Wire graph store via factory when the agent has no explicit store (W-040)."""
        _ = ctx
        agent = self._agent
        if getattr(agent, "graph_store", None) is not None:
            return None
        store = create_graph_store()
        agent.graph_store = store
        if isinstance(store, NoOpGraphStore):
            agent.enable_graph_reasoning = False
        elif not hasattr(agent, "enable_graph_reasoning"):
            agent.enable_graph_reasoning = True
        return None

    async def on_pre_task(self, ctx: AgentPluginContext) -> None:
        augmented = await augment_prompt_with_knowledge(
            self._agent,
            ctx.task_description,
            ctx.context,
        )
        ctx.plugin_state[PLUGIN_STATE_AUGMENTED_TASK_KEY] = augmented
        if augmented != ctx.task_description:
            logger.debug(
                "KnowledgePlugin augmented task for agent %s",
                getattr(self._agent, "agent_id", "?"),
            )
        return None

    async def on_pre_main_loop(
        self,
        ctx: AgentPluginContext,
    ) -> None | PluginShortCircuitResult:
        query = effective_task_description(ctx, ctx.task_description)
        return await try_knowledge_graph_short_circuit(
            self._agent,
            ctx.task_description,
            ctx.context,
            query=query,
        )

    async def on_iteration_start(self, ctx: AgentPluginContext, iteration: int) -> None:
        task = effective_task_description(ctx, ctx.task_description)
        block = await retrieve_iteration_knowledge(
            self._agent,
            task,
            ctx.context,
            iteration,
            options=dict(self._config.options),
        )
        if block is not None:
            ctx.plugin_state[PLUGIN_STATE_ITERATION_CONTEXT_KEY] = block
            logger.debug(
                "KnowledgePlugin iteration %s retrieved %s entities for agent %s",
                iteration,
                block.get("entity_count"),
                getattr(self._agent, "agent_id", "?"),
            )
        else:
            ctx.plugin_state.pop(PLUGIN_STATE_ITERATION_CONTEXT_KEY, None)
        return None
