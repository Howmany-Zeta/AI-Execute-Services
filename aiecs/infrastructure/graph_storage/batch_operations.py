"""
Batch Operations for Graph Storage

Provides efficient batch operations for bulk inserts, updates, and deletes.
Uses PostgreSQL COPY and multi-row INSERT for optimal performance.
"""

import asyncpg  # type: ignore[import-untyped]
import logging
import io
from typing import List, TYPE_CHECKING, Optional
import json

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation

if TYPE_CHECKING:
    from aiecs.infrastructure.graph_storage.protocols import BatchOperationsMixinProtocol

logger = logging.getLogger(__name__)


class BatchOperationsMixin:
    """
    Mixin providing batch operations for graph stores

    This mixin adds efficient batch insert/update/delete methods
    using PostgreSQL-specific optimizations like COPY and multi-row INSERT.

    This mixin expects the class it's mixed into to implement `BatchOperationsMixinProtocol`,
    specifically the `pool` attribute and `_serialize_embedding()` method.

    Example:
        ```python
        class MyGraphStore(GraphStore, BatchOperationsMixin):
            pass

        store = MyGraphStore()
        await store.batch_add_entities([entity1, entity2, ...], batch_size=1000)
        ```
    """

    if TYPE_CHECKING:
        # Type hints for mypy: this mixin expects BatchOperationsMixinProtocol
        pool: Optional[asyncpg.Pool]

        def _serialize_embedding(self, embedding: List[float]) -> Optional[bytes]:
            """Expected method from BatchOperationsMixinProtocol"""
            ...

    async def batch_add_entities(
        self,
        entities: List[Entity],
        batch_size: int = 1000,
        use_copy: bool = True,
    ) -> int:
        """
        Add multiple entities efficiently

        Args:
            entities: List of entities to add
            batch_size: Number of entities per batch
            use_copy: Use PostgreSQL COPY for better performance

        Returns:
            Number of entities added

        Example:
            ```python
            entities = [
                Entity(id="e1", entity_type="Person", properties={"name": "Alice"}),
                Entity(id="e2", entity_type="Person", properties={"name": "Bob"}),
                # ... thousands more
            ]
            count = await store.batch_add_entities(entities, batch_size=1000)
            ```
        """
        if not entities:
            return 0

        if not hasattr(self, "pool") or not self.pool:
            raise RuntimeError("GraphStore not initialized")

        total_added = 0

        if use_copy:
            # Use COPY for maximum performance
            total_added = await self._batch_add_entities_copy(entities)
        else:
            # Use multi-row INSERT
            for i in range(0, len(entities), batch_size):
                batch = entities[i : i + batch_size]
                added = await self._batch_add_entities_insert(batch)
                total_added += added

        logger.info(f"Batch added {total_added} entities")
        return total_added

    async def _batch_add_entities_copy(self, entities: List[Entity]) -> int:
        """
        Add entities using PostgreSQL COPY (fastest method)

        Args:
            entities: List of entities to add

        Returns:
            Number of entities added
        """
        if not entities:
            return 0

        # Prepare data for COPY
        copy_data = io.StringIO()
        for entity in entities:
            # Serialize data
            properties_json = json.dumps(entity.properties)
            embedding_bytes = self._serialize_embedding(entity.embedding) if hasattr(entity, "embedding") and entity.embedding else None

            # Write tab-separated values
            # Format: id \t entity_type \t properties \t embedding
            embedding_hex = embedding_bytes.hex() if embedding_bytes else "\\N"
            copy_data.write(f"{entity.id}\t{entity.entity_type}\t{properties_json}\t{embedding_hex}\n")

        copy_data.seek(0)

        # Execute COPY
        if self.pool is None:
            raise RuntimeError("Connection pool not initialized")
        async with self.pool.acquire() as conn:
            try:
                result = await conn.copy_to_table(
                    "graph_entities",
                    source=copy_data,
                    columns=["id", "entity_type", "properties", "embedding"],
                    format="text",
                )
                # Parse result to get row count
                # Result format: "COPY n" where n is number of rows
                if result and result.startswith("COPY"):
                    return int(result.split()[1])
                return len(entities)
            except asyncpg.UniqueViolationError as e:
                logger.warning(f"Duplicate entities in batch: {e}")
                # Fall back to individual inserts with ON CONFLICT
                return await self._batch_add_entities_insert(entities)
            except Exception as e:
                logger.error(f"COPY failed: {e}")
                # Fall back to INSERT
                return await self._batch_add_entities_insert(entities)

    async def _batch_add_entities_insert(self, entities: List[Entity]) -> int:
        """
        Add entities using multi-row INSERT with ON CONFLICT

        Args:
            entities: List of entities to add

        Returns:
            Number of entities added/updated
        """
        if not entities:
            return 0

        # Build multi-row INSERT
        values_placeholders = []
        values = []

        for i, entity in enumerate(entities):
            base_idx = i * 4
            values_placeholders.append(f"(${base_idx+1}, ${base_idx+2}, ${base_idx+3}::jsonb, ${base_idx+4})")

            properties_json = json.dumps(entity.properties)
            embedding_blob = self._serialize_embedding(entity.embedding) if hasattr(entity, "embedding") and entity.embedding else None

            values.extend(
                [
                    entity.id,
                    entity.entity_type,
                    properties_json,
                    embedding_blob,
                ]
            )

        query = f"""
            INSERT INTO graph_entities (id, entity_type, properties, embedding)
            VALUES {', '.join(values_placeholders)}
            ON CONFLICT (id) DO UPDATE SET
                entity_type = EXCLUDED.entity_type,
                properties = EXCLUDED.properties,
                embedding = EXCLUDED.embedding,
                updated_at = CURRENT_TIMESTAMP
        """

        if self.pool is None:
            raise RuntimeError("Connection pool not initialized")
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(query, *values)
                return len(entities)
            except Exception as e:
                logger.error(f"Batch insert failed: {e}")
                raise

    async def batch_add_relations(
        self,
        relations: List[Relation],
        batch_size: int = 1000,
        use_copy: bool = True,
    ) -> int:
        """
        Add multiple relations efficiently

        Args:
            relations: List of relations to add
            batch_size: Number of relations per batch
            use_copy: Use PostgreSQL COPY for better performance

        Returns:
            Number of relations added

        Example:
            ```python
            relations = [
                Relation(id="r1", source_id="e1", target_id="e2", relation_type="KNOWS", properties={}),
                Relation(id="r2", source_id="e2", target_id="e3", relation_type="KNOWS", properties={}),
                # ... thousands more
            ]
            count = await store.batch_add_relations(relations, batch_size=1000)
            ```
        """
        if not relations:
            return 0

        if not hasattr(self, "pool") or not self.pool:
            raise RuntimeError("GraphStore not initialized")

        total_added = 0

        if use_copy:
            # Use COPY for maximum performance
            total_added = await self._batch_add_relations_copy(relations)
        else:
            # Use multi-row INSERT
            for i in range(0, len(relations), batch_size):
                batch = relations[i : i + batch_size]
                added = await self._batch_add_relations_insert(batch)
                total_added += added

        logger.info(f"Batch added {total_added} relations")
        return total_added

    async def _batch_add_relations_copy(self, relations: List[Relation]) -> int:
        """
        Add relations using PostgreSQL COPY

        Args:
            relations: List of relations to add

        Returns:
            Number of relations added
        """
        if not relations:
            return 0

        # Prepare data for COPY
        copy_data = io.StringIO()
        for relation in relations:
            properties_json = json.dumps(relation.properties)

            # Write tab-separated values
            # Format: id \t relation_type \t source_id \t target_id \t
            # properties \t weight
            copy_data.write(f"{relation.id}\t{relation.relation_type}\t{relation.source_id}\t" f"{relation.target_id}\t{properties_json}\t{relation.weight}\n")

        copy_data.seek(0)

        # Execute COPY
        if self.pool is None:
            raise RuntimeError("Connection pool not initialized")
        async with self.pool.acquire() as conn:
            try:
                result = await conn.copy_to_table(
                    "graph_relations",
                    source=copy_data,
                    columns=[
                        "id",
                        "relation_type",
                        "source_id",
                        "target_id",
                        "properties",
                        "weight",
                    ],
                    format="text",
                )
                if result and result.startswith("COPY"):
                    return int(result.split()[1])
                return len(relations)
            except asyncpg.UniqueViolationError as e:
                logger.warning(f"Duplicate relations in batch: {e}")
                return await self._batch_add_relations_insert(relations)
            except asyncpg.ForeignKeyViolationError as e:
                logger.error(f"Foreign key violation in batch: {e}")
                # Some entities don't exist, fall back to individual inserts
                return await self._batch_add_relations_insert(relations)
            except Exception as e:
                logger.error(f"COPY failed: {e}")
                return await self._batch_add_relations_insert(relations)

    async def _batch_add_relations_insert(self, relations: List[Relation]) -> int:
        """
        Add relations using multi-row INSERT

        Args:
            relations: List of relations to add

        Returns:
            Number of relations added/updated
        """
        if not relations:
            return 0

        # Build multi-row INSERT
        values_placeholders = []
        values = []

        for i, relation in enumerate(relations):
            base_idx = i * 6
            values_placeholders.append(f"(${base_idx+1}, ${base_idx+2}, ${base_idx+3}, ${base_idx+4}, ${base_idx+5}::jsonb, ${base_idx+6})")

            properties_json = json.dumps(relation.properties)

            values.extend(
                [
                    relation.id,
                    relation.relation_type,
                    relation.source_id,
                    relation.target_id,
                    properties_json,
                    relation.weight,
                ]
            )

        query = f"""
            INSERT INTO graph_relations (id, relation_type, source_id, target_id, properties, weight)
            VALUES {', '.join(values_placeholders)}
            ON CONFLICT (id) DO UPDATE SET
                relation_type = EXCLUDED.relation_type,
                source_id = EXCLUDED.source_id,
                target_id = EXCLUDED.target_id,
                properties = EXCLUDED.properties,
                weight = EXCLUDED.weight,
                updated_at = CURRENT_TIMESTAMP
        """

        if self.pool is None:
            raise RuntimeError("Connection pool not initialized")
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(query, *values)
                return len(relations)
            except Exception as e:
                logger.error(f"Batch insert failed: {e}")
                raise

    async def batch_delete_entities(self, entity_ids: List[str], batch_size: int = 1000) -> int:
        """
        Delete multiple entities efficiently

        Args:
            entity_ids: List of entity IDs to delete
            batch_size: Number of entities per batch

        Returns:
            Number of entities deleted
        """
        if not entity_ids:
            return 0

        if not hasattr(self, "pool") or not self.pool:
            raise RuntimeError("GraphStore not initialized")

        total_deleted = 0

        for i in range(0, len(entity_ids), batch_size):
            batch = entity_ids[i : i + batch_size]

            # Use ANY() for efficient batch delete
            query = "DELETE FROM graph_entities WHERE id = ANY($1)"

            if self.pool is None:
                raise RuntimeError("Connection pool not initialized")
            async with self.pool.acquire() as conn:
                result = await conn.execute(query, batch)
                # Parse result: "DELETE n"
                if result and result.startswith("DELETE"):
                    total_deleted += int(result.split()[1])

        logger.info(f"Batch deleted {total_deleted} entities")
        return total_deleted

    async def batch_delete_relations(self, relation_ids: List[str], batch_size: int = 1000) -> int:
        """
        Delete multiple relations efficiently

        Args:
            relation_ids: List of relation IDs to delete
            batch_size: Number of relations per batch

        Returns:
            Number of relations deleted
        """
        if not relation_ids:
            return 0

        if not hasattr(self, "pool") or not self.pool:
            raise RuntimeError("GraphStore not initialized")

        total_deleted = 0

        for i in range(0, len(relation_ids), batch_size):
            batch = relation_ids[i : i + batch_size]

            # Use ANY() for efficient batch delete
            query = "DELETE FROM graph_relations WHERE id = ANY($1)"

            if self.pool is None:
                raise RuntimeError("Connection pool not initialized")
            async with self.pool.acquire() as conn:
                result = await conn.execute(query, batch)
                # Parse result: "DELETE n"
                if result and result.startswith("DELETE"):
                    total_deleted += int(result.split()[1])

        logger.info(f"Batch deleted {total_deleted} relations")
        return total_deleted


def estimate_batch_size(avg_item_size_bytes: int, target_batch_size_mb: int = 10) -> int:
    """
    Estimate optimal batch size based on item size

    Args:
        avg_item_size_bytes: Average size of each item in bytes
        target_batch_size_mb: Target batch size in MB

    Returns:
        Recommended batch size (number of items)

    Example:
        ```python
        # For entities averaging 1KB each
        batch_size = estimate_batch_size(1024, target_batch_size_mb=10)
        # Returns ~10,000
        ```
    """
    target_bytes = target_batch_size_mb * 1024 * 1024
    batch_size = max(100, target_bytes // avg_item_size_bytes)
    return batch_size
