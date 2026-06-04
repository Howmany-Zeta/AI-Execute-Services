# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Graphiti-backed temporal memory store (L1 default implementation).

All graphiti_core imports are deferred to method bodies.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from aiecs.config.config import Settings, get_settings
from aiecs.domain.temporal_memory.models import (
    EpisodeSource,
    IngestEpisodeRequest,
    IngestEpisodeResult,
    SearchFilters,
    TemporalFact,
)
from aiecs.infrastructure.temporal_memory.graphiti.search_filters import (
    build_graphiti_search_filter,
    extract_edge_entity_labels,
    filter_facts_by_excluded_entity_types,
)

logger = logging.getLogger(__name__)

_EPISODE_SOURCE_TO_GRAPHITI = {
    EpisodeSource.MESSAGE: "message",
    EpisodeSource.DOCUMENT: "text",
    EpisodeSource.JSON: "json",
}


def _episode_type_for_source(source: EpisodeSource) -> Any:
    """Lazy import of Graphiti EpisodeType (testable via patch)."""
    from graphiti_core.nodes import EpisodeType

    source_key = _EPISODE_SOURCE_TO_GRAPHITI.get(source, "message")
    return EpisodeType(source_key)


class GraphitiTemporalMemoryStore:
    """
    Graphiti-backed :class:`TemporalMemoryStore`.

    Requires ``pip install aiecs[temporal-graphiti]`` and FalkorDB or Neo4j.
    """

    store_id: str = "graphiti"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._graphiti: Any = None
        self._pending_ingest_tasks: set[asyncio.Task[None]] = set()

    async def initialize(self) -> None:
        graphiti = self._ensure_graphiti()
        if hasattr(graphiti, "build_indices_and_constraints"):
            await graphiti.build_indices_and_constraints()

    async def close(self) -> None:
        pending = list(self._pending_ingest_tasks)
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        self._pending_ingest_tasks.clear()

        driver = getattr(self._graphiti, "driver", None)
        if driver is not None and hasattr(driver, "close"):
            close_fn = driver.close
            if hasattr(close_fn, "__call__"):
                result = close_fn()
                if hasattr(result, "__await__"):
                    await result
        self._graphiti = None

    def _ensure_graphiti(self) -> Any:
        if self._graphiti is not None:
            return self._graphiti

        from graphiti_core.graphiti import Graphiti

        from aiecs.infrastructure.temporal_memory.graphiti.llm_adapter import (
            build_graphiti_llm_clients,
        )

        settings = self._settings
        llm_client, embedder = build_graphiti_llm_clients(settings)
        graph_backend = (settings.tm_graph_backend or "falkordb").strip().lower()
        store_raw = bool(settings.tm_store_raw_episode)

        if graph_backend == "falkordb":
            from graphiti_core.driver.falkordb_driver import FalkorDriver

            url = settings.tm_falkordb_url or "redis://localhost:6379"
            parsed = urlparse(url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 6379
            password = parsed.password or None
            driver = FalkorDriver(host=host, port=port, password=password)
            self._graphiti = Graphiti(
                graph_driver=driver,
                llm_client=llm_client,
                embedder=embedder,
                store_raw_episode_content=store_raw,
            )
        elif graph_backend == "neo4j":
            uri = settings.tm_neo4j_uri or ""
            user = settings.tm_neo4j_user or ""
            password = settings.tm_neo4j_password or ""
            if not uri:
                raise ValueError("TM_NEO4J_URI is required when TM_GRAPH_BACKEND=neo4j")
            self._graphiti = Graphiti(
                uri=uri,
                user=user,
                password=password,
                llm_client=llm_client,
                embedder=embedder,
                store_raw_episode_content=store_raw,
            )
        else:
            raise ValueError(f"Unsupported TM_GRAPH_BACKEND: {graph_backend}")

        return self._graphiti

    async def ingest_episode(self, request: IngestEpisodeRequest) -> IngestEpisodeResult:
        graphiti = self._ensure_graphiti()
        episode_type = _episode_type_for_source(request.source)

        result = await graphiti.add_episode(
            name=request.name,
            episode_body=request.body,
            source_description=request.source_description,
            reference_time=request.reference_time,
            source=episode_type,
            group_id=request.group_id,
            uuid=request.episode_uuid,
        )

        episode = getattr(result, "episode", None)
        episode_id = getattr(episode, "uuid", None) or request.episode_uuid or str(uuid.uuid4())
        edges = getattr(result, "edges", None) or []
        nodes = getattr(result, "nodes", None) or []

        # facts_extracted mirrors Graphiti edge count (entity edges), not a separate fact table.
        return IngestEpisodeResult(
            episode_id=str(episode_id),
            group_id=request.group_id,
            facts_extracted=len(edges),
            entity_count=len(nodes),
            edge_count=len(edges),
        )

    async def ingest_episode_async(
        self,
        request: IngestEpisodeRequest,
        *,
        job_id: str | None = None,
    ) -> str:
        """Schedule ingest on the event loop; return job_id without awaiting Graphiti I/O."""
        job = job_id or str(uuid.uuid4())
        task = asyncio.create_task(
            self._ingest_episode_background(request, job),
            name=f"graphiti-ingest-{job[:8]}",
        )
        self._pending_ingest_tasks.add(task)
        task.add_done_callback(self._on_ingest_task_done)
        return job

    def _on_ingest_task_done(self, task: asyncio.Task[None]) -> None:
        self._pending_ingest_tasks.discard(task)
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.warning("Graphiti background ingest failed: %s", exc, exc_info=exc)

    async def _ingest_episode_background(
        self,
        request: IngestEpisodeRequest,
        job_id: str,
    ) -> None:
        _ = job_id
        await self.ingest_episode(request)

    async def search_facts(
        self,
        query: str,
        *,
        group_ids: list[str],
        limit: int = 10,
        valid_at: datetime | None = None,
        filters: SearchFilters | None = None,
    ) -> list[TemporalFact]:
        graphiti = self._ensure_graphiti()
        center = filters.center_node_uuid if filters else None
        search_filter = build_graphiti_search_filter(valid_at, filters)
        edges = await graphiti.search(
            query,
            group_ids=group_ids,
            num_results=limit,
            center_node_uuid=center,
            search_filter=search_filter,
        )
        facts = [_entity_edge_to_fact(edge, group_ids) for edge in edges]
        if filters and filters.excluded_entity_types:
            facts = filter_facts_by_excluded_entity_types(
                facts,
                filters.excluded_entity_types,
            )
        return facts

    async def _fetch_entity_edge(self, graphiti: Any, fact_id: str) -> Any:
        from graphiti_core.edges import EntityEdge

        return await EntityEdge.get_by_uuid(graphiti.driver, fact_id)

    async def get_fact(self, fact_id: str, *, group_ids: list[str]) -> TemporalFact | None:
        graphiti = self._ensure_graphiti()

        try:
            edge = await self._fetch_entity_edge(graphiti, fact_id)
        except Exception as exc:
            if type(exc).__name__ == "EdgeNotFoundError":
                return None
            logger.debug(
                "Graphiti get_fact by uuid failed for %s (%s); no fallback search",
                fact_id,
                exc,
            )
            return None

        edge_group = str(getattr(edge, "group_id", "") or "")
        if group_ids and edge_group and edge_group not in group_ids:
            return None
        return _entity_edge_to_fact(edge, group_ids or [edge_group])

    async def health_check(self) -> dict[str, Any]:
        try:
            self._ensure_graphiti()
            return {"backend": "graphiti", "ready": True}
        except Exception as exc:
            logger.warning("Graphiti health_check failed: %s", exc)
            return {"backend": "graphiti", "ready": False, "error": str(exc)}


def _entity_edge_to_fact(edge: Any, group_ids: list[str]) -> TemporalFact:
    fact_id = str(getattr(edge, "uuid", "") or uuid.uuid4())
    text = str(getattr(edge, "fact", "") or getattr(edge, "name", "") or "")
    group_id = str(getattr(edge, "group_id", "") or (group_ids[0] if group_ids else ""))
    valid_at = getattr(edge, "valid_at", None)
    invalid_at = getattr(edge, "invalid_at", None)
    if valid_at is not None and getattr(valid_at, "tzinfo", None) is None:
        valid_at = valid_at.replace(tzinfo=timezone.utc)
    if invalid_at is not None and getattr(invalid_at, "tzinfo", None) is None:
        invalid_at = invalid_at.replace(tzinfo=timezone.utc)
    entity_labels = extract_edge_entity_labels(edge)
    metadata: dict[str, Any] = {}
    if entity_labels:
        metadata["entity_labels"] = entity_labels
    return TemporalFact(
        fact_id=fact_id,
        text=text,
        group_id=group_id,
        valid_at=valid_at,
        invalid_at=invalid_at,
        confidence=getattr(edge, "confidence", None),
        source_episode_id=getattr(edge, "episode_uuid", None),
        metadata=metadata,
    )
