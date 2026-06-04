# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Unified read-only retriever: L1 temporal facts + L2 graph_store.search (TM-070).

ADR-003: use :func:`create_graph_store` + duck-type ``search`` only; never import ``aiecs_kg``.
Does not write plugin_state and is not wired into :class:`KnowledgePlugin`.
"""

from __future__ import annotations

import inspect
import logging
from typing import Any

from aiecs.domain.memory.models import RetrievedItem, UnifiedMemoryContext
from aiecs.domain.temporal_memory.engine import TemporalMemoryEngine
from aiecs.domain.temporal_memory.models import TemporalFact
from aiecs.infrastructure.knowledge.noop_graph_store import NoOpGraphStore

logger = logging.getLogger(__name__)

_TEMPORAL_DEFAULT_SCORE = 1.0
_KNOWLEDGE_FIXED_SCORE = 0.8


def _l2_search_available(graph_store: Any | None) -> bool:
    if graph_store is None or isinstance(graph_store, NoOpGraphStore):
        return False
    return callable(getattr(graph_store, "search", None))


def _entity_to_text(entity: Any) -> str:
    """Format a duck-typed L2 entity for merged prompt text."""
    entity_type = getattr(entity, "entity_type", type(entity).__name__)
    entity_id = getattr(entity, "id", str(entity))
    text = f"{entity_type}: {entity_id}"
    properties = getattr(entity, "properties", None)
    if properties:
        props_str = ", ".join(f"{key}={value}" for key, value in properties.items())
        text += f" ({props_str})"
    return text


def _temporal_score(fact: TemporalFact) -> float:
    if fact.confidence is not None:
        return float(fact.confidence)
    return _TEMPORAL_DEFAULT_SCORE


def merge_and_rerank(
    temporal_facts: list[TemporalFact],
    knowledge_entities: list[Any],
    *,
    limit: int,
) -> list[RetrievedItem]:
    """
    Merge L1 facts and L2 entities: score descending; tie → temporal before knowledge.
    """
    items: list[RetrievedItem] = []
    for fact in temporal_facts:
        items.append(
            RetrievedItem(
                source="temporal",
                text=fact.text,
                score=_temporal_score(fact),
                metadata={
                    "fact_id": fact.fact_id,
                    "group_id": fact.group_id,
                },
            )
        )
    for entity in knowledge_entities:
        items.append(
            RetrievedItem(
                source="knowledge",
                text=_entity_to_text(entity),
                score=_KNOWLEDGE_FIXED_SCORE,
                metadata={"entity_id": getattr(entity, "id", None)},
            )
        )

    items.sort(key=lambda item: (-item.score, 0 if item.source == "temporal" else 1))
    return items[:limit]


async def _call_graph_search(graph_store: Any, task: dict[str, Any], *, limit: int) -> list[Any]:
    """Invoke optional async/sync ``graph_store.search`` (duck-typed, same as KnowledgePlugin)."""
    method = getattr(graph_store, "search", None)
    if not callable(method):
        return []
    try:
        result = method(task, limit=limit)
        if inspect.isawaitable(result):
            result = await result
    except TypeError:
        query = TemporalMemoryEngine._extract_search_query(task)
        result = method(query, limit=limit)
        if inspect.isawaitable(result):
            result = await result
    except Exception as exc:
        logger.warning("UnifiedMemoryRetriever L2 search failed: %s", exc)
        return []

    if not isinstance(result, list):
        return []
    return result


async def retrieve_for_task(
    *,
    temporal_engine: TemporalMemoryEngine | None,
    graph_store: Any | None,
    task: dict[str, Any],
    group_ids: list[str],
    limit: int = 10,
) -> UnifiedMemoryContext:
    """
    Retrieve L1 temporal facts and optional L2 knowledge entities for a task.

    Read-only: does not ingest or mutate plugin_state.
    """
    temporal_facts: list[TemporalFact] = []
    if temporal_engine is not None:
        temporal_facts = await temporal_engine.search_for_task(task, group_ids, limit=limit)

    knowledge_entities: list[Any] = []
    if _l2_search_available(graph_store):
        knowledge_entities = await _call_graph_search(graph_store, task, limit=limit)

    merged_items = merge_and_rerank(
        temporal_facts,
        knowledge_entities,
        limit=limit,
    )
    return UnifiedMemoryContext(
        temporal_facts=temporal_facts,
        knowledge_entities=knowledge_entities,
        merged_items=merged_items,
    )
