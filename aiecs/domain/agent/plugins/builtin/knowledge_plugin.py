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

import logging
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar

from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext, PluginShortCircuitResult
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


def effective_task_description(plugin_ctx: AgentPluginContext, fallback: str) -> str:
    """Task string for BUILD_MESSAGES after PRE_TASK (§4.3)."""
    augmented = plugin_ctx.plugin_state.get(PLUGIN_STATE_AUGMENTED_TASK_KEY)
    if isinstance(augmented, str) and augmented:
        return augmented
    return fallback


async def augment_prompt_with_knowledge(
    agent: Any,
    task: str,
    context: dict[str, Any] | None = None,
) -> str:
    """
    Augment a task with cached knowledge graph context.

    Extracted from ``KnowledgeAwareAgent._augment_prompt_with_knowledge`` (E-02).
    """
    _ = context
    graph_store = getattr(agent, "graph_store", None)
    enable_graph_reasoning = getattr(agent, "enable_graph_reasoning", True)
    if graph_store is None or not enable_graph_reasoning:
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
    prioritize = getattr(agent, "_prioritize_knowledge_context", None)
    if callable(prioritize):
        prioritized = prioritize(
            knowledge_items,
            relevance_weight=0.7,
            recency_weight=0.3,
        )
    else:
        prioritized = sorted(knowledge_items, key=lambda pair: pair[1], reverse=True)

    formatted_knowledge = []
    for kg_item, _priority_score in prioritized[:3]:
        data = kg_item.data if hasattr(kg_item, "data") else kg_item
        formatted_knowledge.append(f"- {data['query']}: {data['answer']} (confidence: {data['confidence']:.2f})")

    knowledge_section = "\n\nRELEVANT KNOWLEDGE FROM GRAPH:\n" + "\n".join(formatted_knowledge)
    return task + knowledge_section


class _KnowledgeCacheItem:
    """Wrapper matching ``KnowledgeAwareAgent`` cache-item shape for prioritization."""

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
    """True when the task matches legacy graph-reasoning keyword heuristics."""
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

    Keyword detection uses the original ``task_description``; the graph query uses
    ``query`` (typically ``knowledge.augmented_task`` from PRE_TASK).
    """
    graph_store = getattr(agent, "graph_store", None)
    enable_graph_reasoning = getattr(agent, "enable_graph_reasoning", True)
    if graph_store is None or not enable_graph_reasoning:
        return None
    if not is_graph_short_circuit_query(task_description):
        return None

    reason_with_graph = getattr(agent, "_reason_with_graph", None)
    if not callable(reason_with_graph):
        return None

    graph_result = await reason_with_graph(query or task_description, context)
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


def format_retrieved_knowledge_entities(agent: Any, entities: list[Any]) -> str:
    """Format retrieved entities for prompt injection (``KnowledgeAwareAgent`` parity)."""
    formatter = getattr(agent, "_format_retrieved_knowledge", None)
    if callable(formatter):
        return str(formatter(entities))
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
    """
    Retrieve knowledge for a tool-loop iteration (``KnowledgeAwareAgent._retrieve_relevant_knowledge``).
    """
    retrieve = getattr(agent, "_retrieve_relevant_knowledge", None)
    graph_store = getattr(agent, "graph_store", None)
    enable_graph_reasoning = getattr(agent, "enable_graph_reasoning", True)
    if not callable(retrieve) or graph_store is None or not enable_graph_reasoning:
        return None

    callback = event_callback or context.get("_knowledge_event_callback")
    plugin_options = options or {}

    with _apply_knowledge_options_to_agent(agent, plugin_options):
        entities = await retrieve(task, context, iteration, callback)

    if not entities:
        return None

    formatted = format_retrieved_knowledge_entities(agent, entities)
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
