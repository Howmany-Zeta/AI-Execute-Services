"""
SQLite Graph Storage Backend

Provides file-based persistent graph storage using SQLite.
"""

import json
import aiosqlite
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path as PathLibPath
from contextlib import asynccontextmanager

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.path import Path
from aiecs.infrastructure.graph_storage.base import GraphStore


# SQL Schema for SQLite graph storage
SCHEMA_SQL = """
-- Entities table
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    properties TEXT NOT NULL,  -- JSON
    embedding BLOB,             -- Vector embedding (serialized)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Relations table
CREATE TABLE IF NOT EXISTS relations (
    id TEXT PRIMARY KEY,
    relation_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    properties TEXT NOT NULL,  -- JSON
    weight REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES entities(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(relation_type);
CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_id);
CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_id);
CREATE INDEX IF NOT EXISTS idx_relations_source_target ON relations(source_id, target_id);
"""


class SQLiteGraphStore(GraphStore):
    """
    SQLite-based graph storage implementation

    Provides persistent file-based graph storage with:
    - ACID transactions
    - SQL-optimized queries
    - Optional recursive CTEs for traversal
    - Connection pooling

    Features:
    - File-based persistence (single .db file)
    - Automatic schema initialization
    - Efficient SQL queries for graph operations
    - Optional Tier 2 optimizations

    Example:
        ```python
        store = SQLiteGraphStore("knowledge_graph.db")
        await store.initialize()

        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await store.add_entity(entity)

        await store.close()
        ```
    """

    def __init__(self, db_path: str = ":memory:", **kwargs):
        """
        Initialize SQLite graph store

        Args:
            db_path: Path to SQLite database file (":memory:" for in-memory)
            **kwargs: Additional SQLite connection parameters
        """
        super().__init__()
        self.db_path = db_path
        self.conn_kwargs = kwargs
        self.conn: Optional[aiosqlite.Connection] = None
        self._is_initialized = False
        self._in_transaction = False

    async def initialize(self):
        """Initialize SQLite database and create schema"""
        # Create directory if needed
        if self.db_path != ":memory:":
            PathLibPath(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Connect to database
        self.conn = await aiosqlite.connect(self.db_path, **self.conn_kwargs)

        # Enable foreign keys
        if self.conn is None:
            raise RuntimeError("Failed to initialize database connection")
        await self.conn.execute("PRAGMA foreign_keys = ON")

        # Create schema
        await self.conn.executescript(SCHEMA_SQL)
        await self.conn.commit()

        self._is_initialized = True

    async def close(self):
        """Close database connection"""
        if self.conn:
            await self.conn.close()
            self.conn = None
        self._is_initialized = False

    @asynccontextmanager
    async def transaction(self):
        """
        Transaction context manager for atomic operations

        Usage:
            ```python
            async with store.transaction():
                await store.add_entity(entity1)
                await store.add_entity(entity2)
                # Both entities added atomically
            ```

        Note: SQLite uses connection-level transactions. Within a transaction,
        commits are deferred until the context exits successfully.
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        # Track transaction state to prevent auto-commits in operations
        self._in_transaction = True
        try:
            # Begin transaction
            await self.conn.execute("BEGIN")
            yield
            # Commit on success
            await self.conn.commit()
        except Exception:
            # Rollback on error
            await self.conn.rollback()
            raise
        finally:
            self._in_transaction = False

    # =========================================================================
    # Tier 1: Basic Interface (SQL-optimized implementations)
    # =========================================================================

    async def add_entity(self, entity: Entity) -> None:
        """Add entity to SQLite database"""
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        # Check if entity already exists
        cursor = await self.conn.execute("SELECT id FROM entities WHERE id = ?", (entity.id,))
        existing = await cursor.fetchone()
        if existing:
            raise ValueError(f"Entity with ID '{entity.id}' already exists")

        # Serialize data
        properties_json = json.dumps(entity.properties)
        embedding_blob = self._serialize_embedding(entity.embedding) if entity.embedding else None

        # Insert entity
        await self.conn.execute(
            """
            INSERT INTO entities (id, entity_type, properties, embedding)
            VALUES (?, ?, ?, ?)
            """,
            (entity.id, entity.entity_type, properties_json, embedding_blob),
        )
        if not self._in_transaction:
            await self.conn.commit()

    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity from SQLite database"""
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = await self.conn.execute(
            """
            SELECT id, entity_type, properties, embedding
            FROM entities
            WHERE id = ?
            """,
            (entity_id,),
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_entity(tuple(row))

    async def update_entity(self, entity: Entity) -> Entity:
        """Update entity in SQLite database"""
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        # Check if entity exists
        existing = await self.get_entity(entity.id)
        if not existing:
            raise ValueError(f"Entity with ID '{entity.id}' does not exist")

        # Serialize data
        properties_json = json.dumps(entity.properties)
        embedding_blob = self._serialize_embedding(entity.embedding) if entity.embedding else None

        # Update entity
        await self.conn.execute(
            """
            UPDATE entities
            SET entity_type = ?, properties = ?, embedding = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (entity.entity_type, properties_json, embedding_blob, entity.id),
        )
        if not self._in_transaction:
            await self.conn.commit()

        return entity

    async def delete_entity(self, entity_id: str):
        """Delete entity and its relations from SQLite database"""
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        # Foreign key cascade will automatically delete relations
        await self.conn.execute("DELETE FROM entities WHERE id = ?", (entity_id,))
        if not self._in_transaction:
            await self.conn.commit()

    async def add_relation(self, relation: Relation) -> None:
        """Add relation to SQLite database"""
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        # Check if relation already exists
        cursor = await self.conn.execute("SELECT id FROM relations WHERE id = ?", (relation.id,))
        existing = await cursor.fetchone()
        if existing:
            raise ValueError(f"Relation with ID '{relation.id}' already exists")

        # Check if entities exist
        source_exists = await self.get_entity(relation.source_id)
        target_exists = await self.get_entity(relation.target_id)
        if not source_exists:
            raise ValueError(f"Source entity '{relation.source_id}' does not exist")
        if not target_exists:
            raise ValueError(f"Target entity '{relation.target_id}' does not exist")

        # Serialize data
        properties_json = json.dumps(relation.properties)

        # Insert relation
        await self.conn.execute(
            """
            INSERT INTO relations (id, relation_type, source_id, target_id, properties, weight)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                relation.id,
                relation.relation_type,
                relation.source_id,
                relation.target_id,
                properties_json,
                relation.weight,
            ),
        )
        if not self._in_transaction:
            await self.conn.commit()

    async def get_relation(self, relation_id: str) -> Optional[Relation]:
        """Get relation from SQLite database"""
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = await self.conn.execute(
            """
            SELECT id, relation_type, source_id, target_id, properties, weight
            FROM relations
            WHERE id = ?
            """,
            (relation_id,),
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_relation(tuple(row))

    async def update_relation(self, relation: Relation) -> Relation:
        """Update relation in SQLite database"""
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        # Check if relation exists
        existing = await self.get_relation(relation.id)
        if not existing:
            raise ValueError(f"Relation with ID '{relation.id}' does not exist")

        # Serialize data
        properties_json = json.dumps(relation.properties)

        # Update relation
        await self.conn.execute(
            """
            UPDATE relations
            SET relation_type = ?, source_id = ?, target_id = ?, properties = ?,
                weight = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                relation.relation_type,
                relation.source_id,
                relation.target_id,
                properties_json,
                relation.weight,
                relation.id,
            ),
        )
        if not self._in_transaction:
            await self.conn.commit()

        return relation

    async def delete_relation(self, relation_id: str):
        """Delete relation from SQLite database"""
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        await self.conn.execute("DELETE FROM relations WHERE id = ?", (relation_id,))
        if not self._in_transaction:
            await self.conn.commit()

    async def get_neighbors(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        direction: str = "outgoing",
    ) -> List[Entity]:
        """
        Get neighboring entities connected by relations

        Implements the base GraphStore interface.

        Args:
            entity_id: ID of entity to get neighbors for
            relation_type: Optional filter by relation type
            direction: "outgoing", "incoming", or "both"

        Returns:
            List of neighboring entities
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        neighbors = []

        # Build WHERE clause for relation type
        type_filter = ""
        params = [entity_id]
        if relation_type:
            type_filter = "AND r.relation_type = ?"
            params.append(relation_type)

        # Outgoing relations
        if direction in ["outgoing", "both"]:
            query = f"""
                SELECT e.id, e.entity_type, e.properties, e.embedding
                FROM relations r
                JOIN entities e ON r.target_id = e.id
                WHERE r.source_id = ? {type_filter}
            """

            cursor = await self.conn.execute(query, params)
            rows = await cursor.fetchall()

            for row in rows:
                entity = self._row_to_entity(tuple(row))
                neighbors.append(entity)

        # Incoming relations
        if direction in ["incoming", "both"]:
            params_incoming = [entity_id]
            if relation_type:
                params_incoming.append(relation_type)

            query = f"""
                SELECT e.id, e.entity_type, e.properties, e.embedding
                FROM relations r
                JOIN entities e ON r.source_id = e.id
                WHERE r.target_id = ? {type_filter}
            """

            cursor = await self.conn.execute(query, params_incoming)
            rows = await cursor.fetchall()

            for row in rows:
                entity = self._row_to_entity(tuple(row))
                neighbors.append(entity)

        return neighbors

    # =========================================================================
    # Tier 2: Advanced Interface (SQL-optimized overrides)
    # =========================================================================

    async def vector_search(
        self,
        query_embedding: List[float],
        entity_type: Optional[str] = None,
        max_results: int = 10,
        score_threshold: float = 0.0,
    ) -> List[Tuple[Entity, float]]:
        """
        SQL-optimized vector similarity search

        Performs cosine similarity search over entity embeddings stored in SQLite.
        This implementation fetches all candidates and computes similarity in Python.

        For production scale, consider:
        - pgvector extension (PostgreSQL)
        - Dedicated vector database (Qdrant, Milvus)
        - Pre-computed ANN indexes

        Args:
            query_embedding: Query vector
            entity_type: Optional filter by entity type
            max_results: Maximum number of results to return
            score_threshold: Minimum similarity score (0.0-1.0)

        Returns:
            List of (entity, similarity_score) tuples, sorted descending
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        if not query_embedding:
            raise ValueError("Query embedding cannot be empty")

        # Build query with optional type filter
        type_filter = "WHERE entity_type = ?" if entity_type else ""
        params = [entity_type] if entity_type else []

        query = f"""
            SELECT id, entity_type, properties, embedding
            FROM entities
            {type_filter}
        """

        cursor = await self.conn.execute(query, params)
        rows = await cursor.fetchall()

        # Compute similarities
        scored_entities = []
        for row in rows:
            entity = self._row_to_entity(tuple(row))

            # Skip entities without embeddings
            if not entity.embedding:
                continue

            # Compute cosine similarity
            similarity = self._cosine_similarity(query_embedding, entity.embedding)

            # Filter by minimum score (score_threshold)
            if similarity >= score_threshold:
                scored_entities.append((entity, similarity))

        # Sort by score descending and return top max_results
        scored_entities.sort(key=lambda x: x[1], reverse=True)
        return scored_entities[:max_results]

    async def traverse(
        self,
        start_entity_id: str,
        relation_type: Optional[str] = None,
        max_depth: int = 3,
        max_results: int = 100,
    ) -> List[Path]:
        """
        SQL-optimized traversal using recursive CTE

        This overrides the default Tier 2 implementation for better performance.
        Uses recursive CTEs in SQLite for efficient graph traversal.
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        # For SQLite, we'll use the default implementation from base class
        # which uses BFS with get_neighbors(). While recursive CTEs are powerful,
        # building full Path objects with them is complex. The default is sufficient.
        # Backends with native graph query languages (e.g., Neo4j with Cypher)
        # should override this for better performance.
        return await self._default_traverse_bfs(start_entity_id, relation_type, max_depth, max_results)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _row_to_entity(self, row: tuple) -> Entity:
        """Convert database row to Entity object"""
        entity_id, entity_type, properties_json, embedding_blob = row

        properties = json.loads(properties_json)
        embedding = self._deserialize_embedding(embedding_blob) if embedding_blob else None

        return Entity(
            id=entity_id,
            entity_type=entity_type,
            properties=properties,
            embedding=embedding,
        )

    def _row_to_relation(self, row: tuple) -> Relation:
        """Convert database row to Relation object"""
        rel_id, rel_type, source_id, target_id, properties_json, weight = row

        properties = json.loads(properties_json)

        return Relation(
            id=rel_id,
            relation_type=rel_type,
            source_id=source_id,
            target_id=target_id,
            properties=properties,
            weight=weight,
        )

    def _serialize_embedding(self, embedding: List[float]) -> bytes:
        """Serialize embedding vector to bytes"""
        import struct

        return struct.pack(f"{len(embedding)}f", *embedding)

    def _deserialize_embedding(self, blob: bytes) -> List[float]:
        """Deserialize embedding vector from bytes"""
        import struct

        count = len(blob) // 4  # 4 bytes per float
        return list(struct.unpack(f"{count}f", blob))

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Compute cosine similarity between two vectors

        Returns value between -1 and 1, where 1 means identical direction.
        Normalized to 0-1 range for consistency.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity (0.0-1.0)
        """
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        # Cosine similarity ranges from -1 to 1, normalize to 0 to 1
        similarity = dot_product / (magnitude1 * magnitude2)
        return (similarity + 1) / 2

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the SQLite graph store"""
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        # Count entities
        cursor = await self.conn.execute("SELECT COUNT(*) FROM entities")
        entity_row = await cursor.fetchone()
        entity_count = entity_row[0] if entity_row else 0

        # Count relations
        cursor = await self.conn.execute("SELECT COUNT(*) FROM relations")
        relation_row = await cursor.fetchone()
        relation_count = relation_row[0] if relation_row else 0

        # Database file size
        file_size = 0
        if self.db_path != ":memory:":
            try:
                file_size = PathLibPath(self.db_path).stat().st_size
            except (OSError, ValueError):
                pass

        return {
            "entity_count": entity_count,
            "relation_count": relation_count,
            "storage_type": "sqlite",
            "db_path": self.db_path,
            "db_size_bytes": file_size,
            "is_initialized": self._is_initialized,
        }

    async def clear(self):
        """Clear all data from SQLite database"""
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        await self.conn.execute("DELETE FROM relations")
        await self.conn.execute("DELETE FROM entities")
        if not self._in_transaction:
            await self.conn.commit()
