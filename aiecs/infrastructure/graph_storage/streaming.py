"""
Streaming Support for Graph Storage

Provides streaming export and import capabilities for large graphs,
enabling efficient handling of millions of entities and relations.
"""

import json
import logging
from typing import AsyncIterator, Optional, Dict, Any, List
from enum import Enum
import gzip
from pathlib import Path
from datetime import datetime

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects"""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class StreamFormat(str, Enum):
    """Streaming export format"""

    JSONL = "jsonl"  # JSON Lines (one JSON object per line)
    JSON = "json"  # Standard JSON array
    CSV = "csv"  # CSV format


class GraphStreamExporter:
    """
    Stream large graphs to files

    Exports entities and relations in chunks to avoid loading
    everything into memory at once.

    Example:
        ```python
        exporter = GraphStreamExporter(store)

        # Export to JSONL (recommended for large graphs)
        await exporter.export_to_file(
            "graph_export.jsonl",
            format=StreamFormat.JSONL,
            compress=True
        )

        # Export with filtering
        await exporter.export_entities(
            "persons.jsonl",
            entity_type="Person",
            batch_size=1000
        )
        ```
    """

    def __init__(self, store: Any):
        """
        Initialize exporter

        Args:
            store: Graph store instance
        """
        self.store = store

    async def export_to_file(
        self,
        filepath: str,
        format: StreamFormat = StreamFormat.JSONL,
        compress: bool = False,
        batch_size: int = 1000,
        entity_type: Optional[str] = None,
        include_relations: bool = True,
    ) -> Dict[str, Any]:
        """
        Export entire graph to file

        Args:
            filepath: Output file path
            format: Export format
            compress: Enable gzip compression
            batch_size: Streaming batch size
            entity_type: Filter entities by type
            include_relations: Include relations in export

        Returns:
            Dictionary with export statistics

        Example:
            ```python
            stats = await exporter.export_to_file(
                "graph.jsonl.gz",
                format=StreamFormat.JSONL,
                compress=True,
                batch_size=5000
            )
            print(f"Exported {stats['entity_count']} entities")
            ```
        """
        Path(filepath)

        # Add .gz extension if compressing
        if compress and not filepath.endswith(".gz"):
            filepath = f"{filepath}.gz"

        entity_count = 0
        relation_count = 0

        # Open file (with compression if requested)
        if compress:
            import gzip

            file = gzip.open(filepath, "wt", encoding="utf-8")
        else:
            file = open(filepath, "w", encoding="utf-8")

        try:
            # Write header for JSON format
            if format == StreamFormat.JSON:
                file.write('{"entities": [')

            # Stream entities
            first = True
            async for entity in self.stream_entities(entity_type=entity_type, batch_size=batch_size):
                if format == StreamFormat.JSONL:
                    json.dump(
                        {"type": "entity", "data": entity.model_dump()},
                        file,
                        cls=DateTimeEncoder,
                    )
                    file.write("\n")
                elif format == StreamFormat.JSON:
                    if not first:
                        file.write(",")
                    json.dump(entity.model_dump(), file, cls=DateTimeEncoder)
                    first = False

                entity_count += 1

                # Log progress
                if entity_count % 10000 == 0:
                    logger.info(f"Exported {entity_count} entities...")

            # Stream relations if requested
            if include_relations:
                if format == StreamFormat.JSON:
                    file.write('], "relations": [')
                    first = True

                async for relation in self.stream_relations(batch_size=batch_size):
                    if format == StreamFormat.JSONL:
                        json.dump(
                            {
                                "type": "relation",
                                "data": relation.model_dump(),
                            },
                            file,
                            cls=DateTimeEncoder,
                        )
                        file.write("\n")
                    elif format == StreamFormat.JSON:
                        if not first:
                            file.write(",")
                        json.dump(relation.model_dump(), file, cls=DateTimeEncoder)
                        first = False

                    relation_count += 1

                    if relation_count % 10000 == 0:
                        logger.info(f"Exported {relation_count} relations...")

            # Write footer for JSON format
            if format == StreamFormat.JSON:
                file.write("]}")

        finally:
            file.close()

        logger.info(f"Export complete: {entity_count} entities, {relation_count} relations")

        return {
            "entity_count": entity_count,
            "relation_count": relation_count,
            "filepath": filepath,
            "compressed": compress,
        }

    async def stream_entities(self, entity_type: Optional[str] = None, batch_size: int = 1000) -> AsyncIterator[Entity]:
        """
        Stream entities in batches

        Args:
            entity_type: Filter by entity type
            batch_size: Batch size for streaming

        Yields:
            Entity instances
        """
        # Use pagination to stream efficiently
        if hasattr(self.store, "paginate_entities"):
            cursor = None
            while True:
                page = await self.store.paginate_entities(
                    entity_type=entity_type,
                    page_size=batch_size,
                    cursor=cursor,
                )

                for entity in page.items:
                    yield entity

                if not page.page_info.has_next_page:
                    break

                cursor = page.page_info.end_cursor
        else:
            # Fallback: load all and yield
            entities = await self.store.get_all_entities(entity_type=entity_type)
            for entity in entities:
                yield entity

    async def stream_relations(self, relation_type: Optional[str] = None, batch_size: int = 1000) -> AsyncIterator[Relation]:
        """
        Stream relations in batches

        Args:
            relation_type: Filter by relation type
            batch_size: Batch size for streaming

        Yields:
            Relation instances
        """
        # Use pagination if available
        if hasattr(self.store, "paginate_relations"):
            cursor = None
            while True:
                page = await self.store.paginate_relations(
                    relation_type=relation_type,
                    page_size=batch_size,
                    cursor=cursor,
                )

                for relation in page.items:
                    yield relation

                if not page.page_info.has_next_page:
                    break

                cursor = page.page_info.end_cursor
        else:
            # Fallback: get all relations (this may be memory intensive)
            # Backends should implement paginate_relations
            logger.warning("Pagination not available, loading all relations")
            # For now, yield nothing - backends must implement pagination
            return

    async def export_entities(
        self,
        filepath: str,
        entity_type: Optional[str] = None,
        batch_size: int = 1000,
        compress: bool = False,
    ) -> int:
        """
        Export only entities to file

        Args:
            filepath: Output file path
            entity_type: Filter by entity type
            batch_size: Streaming batch size
            compress: Enable gzip compression

        Returns:
            Number of entities exported
        """
        if compress:
            file = gzip.open(filepath, "wt", encoding="utf-8")
        else:
            file = open(filepath, "w", encoding="utf-8")

        count = 0
        try:
            async for entity in self.stream_entities(entity_type=entity_type, batch_size=batch_size):
                json.dump(entity.model_dump(), file, cls=DateTimeEncoder)
                file.write("\n")
                count += 1
        finally:
            file.close()

        return count


class GraphStreamImporter:
    """
    Stream large graphs from files

    Imports entities and relations in chunks to avoid memory issues.

    Example:
        ```python
        importer = GraphStreamImporter(store)

        # Import from JSONL file
        stats = await importer.import_from_file(
            "graph_export.jsonl.gz",
            batch_size=1000
        )
        print(f"Imported {stats['entity_count']} entities")
        ```
    """

    def __init__(self, store: Any):
        """
        Initialize importer

        Args:
            store: Graph store instance
        """
        self.store = store

    async def import_from_file(
        self,
        filepath: str,
        batch_size: int = 1000,
        format: StreamFormat = StreamFormat.JSONL,
    ) -> Dict[str, int]:
        """
        Import graph from file

        Args:
            filepath: Input file path
            batch_size: Batch size for bulk operations
            format: File format

        Returns:
            Dictionary with import statistics
        """
        # Detect compression
        compressed = filepath.endswith(".gz")

        # Open file
        if compressed:
            file = gzip.open(filepath, "rt", encoding="utf-8")
        else:
            file = open(filepath, "r", encoding="utf-8")

        entity_count = 0
        relation_count = 0

        entity_batch = []
        relation_batch = []

        try:
            if format == StreamFormat.JSONL:
                for line in file:
                    if not line.strip():
                        continue

                    data = json.loads(line)

                    if data.get("type") == "entity":
                        entity_batch.append(Entity(**data["data"]))
                    elif data.get("type") == "relation":
                        relation_batch.append(Relation(**data["data"]))
                    else:
                        # Assume entity if no type specified
                        entity_batch.append(Entity(**data))

                    # Flush batches
                    if len(entity_batch) >= batch_size:
                        await self._import_entity_batch(entity_batch)
                        entity_count += len(entity_batch)
                        entity_batch.clear()
                        logger.info(f"Imported {entity_count} entities...")

                    if len(relation_batch) >= batch_size:
                        await self._import_relation_batch(relation_batch)
                        relation_count += len(relation_batch)
                        relation_batch.clear()
                        logger.info(f"Imported {relation_count} relations...")

            # Flush remaining batches
            if entity_batch:
                await self._import_entity_batch(entity_batch)
                entity_count += len(entity_batch)

            if relation_batch:
                await self._import_relation_batch(relation_batch)
                relation_count += len(relation_batch)

        finally:
            file.close()

        logger.info(f"Import complete: {entity_count} entities, {relation_count} relations")

        return {"entity_count": entity_count, "relation_count": relation_count}

    async def _import_entity_batch(self, entities: list[Entity]) -> None:
        """Import a batch of entities"""
        if hasattr(self.store, "batch_add_entities"):
            await self.store.batch_add_entities(entities)
        else:
            for entity in entities:
                await self.store.add_entity(entity)

    async def _import_relation_batch(self, relations: list[Relation]) -> None:
        """Import a batch of relations"""
        if hasattr(self.store, "batch_add_relations"):
            await self.store.batch_add_relations(relations)
        else:
            for relation in relations:
                await self.store.add_relation(relation)


async def stream_subgraph(
    store: Any,
    entity_ids: list[str],
    max_depth: int = 2,
    batch_size: int = 100,
) -> AsyncIterator[tuple[Entity, list[Relation]]]:
    """
    Stream a subgraph around specific entities

    Yields entities with their relations in manageable chunks.

    Args:
        store: Graph store instance
        entity_ids: Starting entity IDs
        max_depth: Maximum depth to traverse
        batch_size: Batch size for processing

    Yields:
        Tuples of (entity, relations) for each entity in subgraph

    Example:
        ```python
        async for entity, relations in stream_subgraph(store, ["person_1"], max_depth=2):
            print(f"Entity: {entity.id}, Relations: {len(relations)}")
        ```
    """
    visited = set()
    current_level = entity_ids
    depth = 0

    while current_level and depth <= max_depth:
        # Process current level in batches
        for i in range(0, len(current_level), batch_size):
            batch = current_level[i : i + batch_size]
            next_level_batch = []

            for entity_id in batch:
                if entity_id in visited:
                    continue

                visited.add(entity_id)

                # Get entity
                entity = await store.get_entity(entity_id)
                if not entity:
                    continue

                # Get relations
                neighbors = await store.get_neighbors(entity_id, direction="both")
                # For now, return empty relations list - would need to fetch
                # actual relations
                relations: List[Any] = []

                # Collect next level
                for neighbor in neighbors:
                    if neighbor.id not in visited:
                        next_level_batch.append(neighbor.id)

                yield (entity, relations)

            # Add to next level
            current_level.extend(next_level_batch)

        depth += 1
