"""
PostgreSQL Graph Storage Backend

Provides production-grade graph storage using PostgreSQL with:
- Connection pooling via asyncpg
- Transaction support
- Recursive CTEs for efficient graph traversal
- Optional pgvector support for vector similarity search
"""

import json
import asyncpg  # type: ignore[import-untyped]
import logging
from typing import Any, Dict, List, Optional, cast
from contextlib import asynccontextmanager
import numpy as np

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.path import Path
from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.config.config import get_settings

logger = logging.getLogger(__name__)


# PostgreSQL Schema for graph storage
SCHEMA_SQL = """
-- Entities table
CREATE TABLE IF NOT EXISTS graph_entities (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}',
    embedding BYTEA,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Relations table
CREATE TABLE IF NOT EXISTS graph_relations (
    id TEXT PRIMARY KEY,
    relation_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}',
    weight REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES graph_entities(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES graph_entities(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_graph_entities_type ON graph_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_graph_entities_properties ON graph_entities USING GIN(properties);
CREATE INDEX IF NOT EXISTS idx_graph_relations_type ON graph_relations(relation_type);
CREATE INDEX IF NOT EXISTS idx_graph_relations_source ON graph_relations(source_id);
CREATE INDEX IF NOT EXISTS idx_graph_relations_target ON graph_relations(target_id);
CREATE INDEX IF NOT EXISTS idx_graph_relations_source_target ON graph_relations(source_id, target_id);
CREATE INDEX IF NOT EXISTS idx_graph_relations_properties ON graph_relations USING GIN(properties);

-- Optional: Add pgvector extension support (if available)
-- CREATE EXTENSION IF NOT EXISTS vector;
-- ALTER TABLE graph_entities ADD COLUMN IF NOT EXISTS embedding_vector vector(1536);
-- CREATE INDEX IF NOT EXISTS idx_graph_entities_embedding ON graph_entities USING ivfflat (embedding_vector vector_cosine_ops);
"""


class PostgresGraphStore(GraphStore):
    """
    PostgreSQL-based graph storage implementation

    Provides production-grade persistent graph storage with:
    - Connection pooling via asyncpg
    - ACID transactions
    - SQL-optimized queries with recursive CTEs
    - JSONB for flexible property storage
    - Optional pgvector for vector similarity search

    Features:
    - Production-ready with connection pooling
    - Efficient graph traversal using WITH RECURSIVE
    - Automatic schema initialization
    - Transaction support
    - JSONB indexing for fast property queries

    Example:
        ```python
        from aiecs.infrastructure.graph_storage import PostgresGraphStore

        # Using config from settings
        store = PostgresGraphStore()
        await store.initialize()

        # Or with custom config
        store = PostgresGraphStore(
            host="localhost",
            port=5432,
            user="postgres",
            password="password",
            database="knowledge_graph"
        )
        await store.initialize()

        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await store.add_entity(entity)

        await store.close()
        ```
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        min_pool_size: int = 5,
        max_pool_size: int = 20,
        enable_pgvector: bool = False,
        pool: Optional[asyncpg.Pool] = None,
        database_manager: Optional[Any] = None,
        **kwargs,
    ):
        """
        Initialize PostgreSQL graph store

        Args:
            host: PostgreSQL host (defaults from config)
            port: PostgreSQL port (defaults from config)
            user: PostgreSQL user (defaults from config)
            password: PostgreSQL password (defaults from config)
            database: Database name (defaults from config)
            min_pool_size: Minimum connection pool size
            max_pool_size: Maximum connection pool size
            enable_pgvector: Enable pgvector extension for vector search
            pool: Optional existing asyncpg pool to reuse (from DatabaseManager)
            database_manager: Optional DatabaseManager instance to reuse its pool
            **kwargs: Additional asyncpg connection parameters
        """
        super().__init__()

        # Option 1: Reuse existing pool
        self._external_pool = pool
        self._owns_pool = pool is None and database_manager is None

        # Option 2: Reuse DatabaseManager's pool
        if database_manager is not None:
            self._external_pool = getattr(database_manager, "connection_pool", None)
            if self._external_pool:
                logger.info("Reusing DatabaseManager's connection pool")
                self._owns_pool = False

        # Load config from settings if not provided (needed for own pool creation)
        # Support both connection string (dsn) and individual parameters
        self.dsn = None
        if not all([host, port, user, password, database]):
            settings = get_settings()
            db_config = settings.database_config

            # Check if connection string (dsn) is provided (for cloud
            # databases)
            if "dsn" in db_config:
                self.dsn = db_config["dsn"]
                # Still set defaults for logging/display purposes
                host = host or "cloud"
                port = port or 5432
                user = user or "postgres"
                password = password or ""
                database = database or "aiecs"
            else:
                # Use individual parameters (for local databases)
                host = host or db_config.get("host", "localhost")
                port = port or db_config.get("port", 5432)
                user = user or db_config.get("user", "postgres")
                password = password or db_config.get("password", "")
                database = database or db_config.get("database", "aiecs")

        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.enable_pgvector = enable_pgvector
        self.conn_kwargs = kwargs

        self.pool: Optional[asyncpg.Pool] = self._external_pool
        self._is_initialized = False
        self._transaction_conn: Optional[asyncpg.Connection] = None

    def _ensure_pool(self) -> asyncpg.Pool:
        """Ensure pool is initialized and return it."""
        if self.pool is None:
            raise RuntimeError("Connection pool not initialized")
        return self.pool

    async def initialize(self):
        """Initialize PostgreSQL connection pool and create schema"""
        try:
            # Create connection pool only if we don't have an external one
            if self._owns_pool:
                # Use connection string (dsn) if available (for cloud databases)
                # Otherwise use individual parameters (for local databases)
                if self.dsn:
                    self.pool = await asyncpg.create_pool(
                        dsn=self.dsn,
                        min_size=self.min_pool_size,
                        max_size=self.max_pool_size,
                        **self.conn_kwargs,
                    )
                    logger.info("PostgreSQL connection pool created using connection string (cloud/local)")
                else:
                    self.pool = await asyncpg.create_pool(
                        host=self.host,
                        port=self.port,
                        user=self.user,
                        password=self.password,
                        database=self.database,
                        min_size=self.min_pool_size,
                        max_size=self.max_pool_size,
                        **self.conn_kwargs,
                    )
                    logger.info(f"PostgreSQL connection pool created: {self.host}:{self.port}/{self.database}")
            else:
                logger.info("Using external PostgreSQL connection pool (shared with AIECS DatabaseManager)")

            # Create schema
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                # Optionally enable pgvector first
                if self.enable_pgvector:
                    try:
                        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                        logger.info("pgvector extension enabled")
                    except Exception as e:
                        logger.warning(f"Failed to enable pgvector: {e}. Continuing without vector support.")
                        self.enable_pgvector = False

                # Execute schema creation
                await conn.execute(SCHEMA_SQL)

                # Add vector column if pgvector is enabled
                if self.enable_pgvector:
                    try:
                        # Check if vector column exists
                        column_exists = await conn.fetchval(
                            """
                            SELECT EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name = 'graph_entities'
                                AND column_name = 'embedding_vector'
                            )
                        """
                        )

                        if not column_exists:
                            # Add vector column (default dimension 1536, can be
                            # adjusted)
                            await conn.execute(
                                """
                                ALTER TABLE graph_entities
                                ADD COLUMN embedding_vector vector(1536)
                            """
                            )
                            logger.info("Added embedding_vector column")

                        # Create index if it doesn't exist
                        index_exists = await conn.fetchval(
                            """
                            SELECT EXISTS (
                                SELECT 1 FROM pg_indexes
                                WHERE tablename = 'graph_entities'
                                AND indexname = 'idx_graph_entities_embedding'
                            )
                        """
                        )

                        if not index_exists:
                            await conn.execute(
                                """
                                CREATE INDEX idx_graph_entities_embedding
                                ON graph_entities USING ivfflat (embedding_vector vector_cosine_ops)
                                WITH (lists = 100)
                            """
                            )
                            logger.info("Created vector similarity index")
                    except Exception as e:
                        logger.warning(f"Failed to set up pgvector column/index: {e}")

            self._is_initialized = True
            logger.info("PostgreSQL graph store initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL graph store: {e}")
            raise

    async def close(self):
        """Close database connection pool (only if we own it)"""
        if self.pool and self._owns_pool:
            await self.pool.close()
            self.pool = None
            logger.info("PostgreSQL connection pool closed")
        elif self.pool and not self._owns_pool:
            logger.info("Detaching from shared PostgreSQL connection pool (not closing)")
            self.pool = None
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
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        pool = self._ensure_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Store connection for use within transaction
                old_conn = self._transaction_conn
                self._transaction_conn = conn
                try:
                    yield conn
                finally:
                    self._transaction_conn = old_conn

    async def _get_connection(self):
        """Get connection from pool or transaction"""
        if self._transaction_conn:
            return self._transaction_conn
        return self.pool.acquire()

    # =========================================================================
    # Tier 1: Basic Interface (PostgreSQL-optimized implementations)
    # =========================================================================

    async def add_entity(self, entity: Entity) -> None:
        """Add entity to PostgreSQL database"""
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        # Serialize data
        properties_json = json.dumps(entity.properties)
        embedding_blob = self._serialize_embedding(entity.embedding) if entity.embedding else None

        # Use connection from transaction or pool
        if self._transaction_conn:
            conn = self._transaction_conn
            await conn.execute(
                """
                INSERT INTO graph_entities (id, entity_type, properties, embedding)
                VALUES ($1, $2, $3::jsonb, $4)
                ON CONFLICT (id) DO UPDATE SET
                    entity_type = EXCLUDED.entity_type,
                    properties = EXCLUDED.properties,
                    embedding = EXCLUDED.embedding,
                    updated_at = CURRENT_TIMESTAMP
                """,
                entity.id,
                entity.entity_type,
                properties_json,
                embedding_blob,
            )
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO graph_entities (id, entity_type, properties, embedding)
                    VALUES ($1, $2, $3::jsonb, $4)
                    ON CONFLICT (id) DO UPDATE SET
                        entity_type = EXCLUDED.entity_type,
                        properties = EXCLUDED.properties,
                        embedding = EXCLUDED.embedding,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    entity.id,
                    entity.entity_type,
                    properties_json,
                    embedding_blob,
                )

    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity from PostgreSQL database"""
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        if self._transaction_conn:
            conn = self._transaction_conn
            row = await conn.fetchrow(
                """
                SELECT id, entity_type, properties, embedding
                FROM graph_entities
                WHERE id = $1
                """,
                entity_id,
            )
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, entity_type, properties, embedding
                    FROM graph_entities
                    WHERE id = $1
                    """,
                    entity_id,
                )

        if not row:
            return None

        # Deserialize
        properties = json.loads(row["properties"]) if isinstance(row["properties"], str) else row["properties"]
        embedding_raw = self._deserialize_embedding(row["embedding"]) if row["embedding"] else None
        embedding: Optional[List[float]] = cast(List[float], embedding_raw.tolist()) if embedding_raw is not None else None

        return Entity(
            id=row["id"],
            entity_type=row["entity_type"],
            properties=properties,
            embedding=embedding,
        )

    async def update_entity(self, entity: Entity) -> None:
        """Update entity in PostgreSQL database"""
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        properties_json = json.dumps(entity.properties)
        embedding_blob = self._serialize_embedding(entity.embedding) if entity.embedding else None

        if self._transaction_conn:
            conn = self._transaction_conn
            result = await conn.execute(
                """
                UPDATE graph_entities
                SET entity_type = $2, properties = $3::jsonb, embedding = $4, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
                """,
                entity.id,
                entity.entity_type,
                properties_json,
                embedding_blob,
            )
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE graph_entities
                    SET entity_type = $2, properties = $3::jsonb, embedding = $4, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                    """,
                    entity.id,
                    entity.entity_type,
                    properties_json,
                    embedding_blob,
                )

        if result == "UPDATE 0":
            raise ValueError(f"Entity with ID '{entity.id}' not found")

    async def delete_entity(self, entity_id: str) -> None:
        """Delete entity from PostgreSQL database"""
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        if self._transaction_conn:
            conn = self._transaction_conn
            result = await conn.execute("DELETE FROM graph_entities WHERE id = $1", entity_id)
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                result = await conn.execute("DELETE FROM graph_entities WHERE id = $1", entity_id)

        if result == "DELETE 0":
            raise ValueError(f"Entity with ID '{entity_id}' not found")

    async def add_relation(self, relation: Relation) -> None:
        """Add relation to PostgreSQL database"""
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        properties_json = json.dumps(relation.properties)

        if self._transaction_conn:
            conn = self._transaction_conn
            await conn.execute(
                """
                INSERT INTO graph_relations (id, relation_type, source_id, target_id, properties, weight)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                ON CONFLICT (id) DO UPDATE SET
                    relation_type = EXCLUDED.relation_type,
                    source_id = EXCLUDED.source_id,
                    target_id = EXCLUDED.target_id,
                    properties = EXCLUDED.properties,
                    weight = EXCLUDED.weight,
                    updated_at = CURRENT_TIMESTAMP
                """,
                relation.id,
                relation.relation_type,
                relation.source_id,
                relation.target_id,
                properties_json,
                relation.weight,
            )
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO graph_relations (id, relation_type, source_id, target_id, properties, weight)
                    VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                    ON CONFLICT (id) DO UPDATE SET
                        relation_type = EXCLUDED.relation_type,
                        source_id = EXCLUDED.source_id,
                        target_id = EXCLUDED.target_id,
                        properties = EXCLUDED.properties,
                        weight = EXCLUDED.weight,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    relation.id,
                    relation.relation_type,
                    relation.source_id,
                    relation.target_id,
                    properties_json,
                    relation.weight,
                )

    async def get_relation(self, relation_id: str) -> Optional[Relation]:
        """Get relation from PostgreSQL database"""
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        if self._transaction_conn:
            conn = self._transaction_conn
            row = await conn.fetchrow(
                """
                SELECT id, relation_type, source_id, target_id, properties, weight
                FROM graph_relations
                WHERE id = $1
                """,
                relation_id,
            )
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, relation_type, source_id, target_id, properties, weight
                    FROM graph_relations
                    WHERE id = $1
                    """,
                    relation_id,
                )

        if not row:
            return None

        properties = json.loads(row["properties"]) if isinstance(row["properties"], str) else row["properties"]

        return Relation(
            id=row["id"],
            relation_type=row["relation_type"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            properties=properties,
            weight=float(row["weight"]) if row["weight"] else 1.0,
        )

    async def delete_relation(self, relation_id: str) -> None:
        """Delete relation from PostgreSQL database"""
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        if self._transaction_conn:
            conn = self._transaction_conn
            result = await conn.execute("DELETE FROM graph_relations WHERE id = $1", relation_id)
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                result = await conn.execute("DELETE FROM graph_relations WHERE id = $1", relation_id)

        if result == "DELETE 0":
            raise ValueError(f"Relation with ID '{relation_id}' not found")

    async def get_neighbors(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        direction: str = "outgoing",
    ) -> List[Entity]:
        """Get neighboring entities (optimized with SQL)"""
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        # Build query based on direction
        if direction == "outgoing":
            query = """
                SELECT DISTINCT e.id, e.entity_type, e.properties, e.embedding
                FROM graph_entities e
                JOIN graph_relations r ON e.id = r.target_id
                WHERE r.source_id = $1
            """
        elif direction == "incoming":
            query = """
                SELECT DISTINCT e.id, e.entity_type, e.properties, e.embedding
                FROM graph_entities e
                JOIN graph_relations r ON e.id = r.source_id
                WHERE r.target_id = $1
            """
        else:  # both
            query = """
                SELECT DISTINCT e.id, e.entity_type, e.properties, e.embedding
                FROM graph_entities e
                WHERE e.id IN (
                    SELECT target_id FROM graph_relations WHERE source_id = $1
                    UNION
                    SELECT source_id FROM graph_relations WHERE target_id = $1
                )
            """

        # Add relation type filter if specified
        params = [entity_id]
        if relation_type:
            if direction == "both":
                query = query.replace(
                    "SELECT target_id FROM graph_relations WHERE source_id = $1",
                    "SELECT target_id FROM graph_relations WHERE source_id = $1 AND relation_type = $2",
                )
                query = query.replace(
                    "SELECT source_id FROM graph_relations WHERE target_id = $1",
                    "SELECT source_id FROM graph_relations WHERE target_id = $1 AND relation_type = $2",
                )
            else:
                query += " AND r.relation_type = $2"
            params.append(relation_type)

        if self._transaction_conn:
            conn = self._transaction_conn
            rows = await conn.fetch(query, *params)
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(query, *params)

        entities = []
        for row in rows:
            properties = json.loads(row["properties"]) if isinstance(row["properties"], str) else row["properties"]
            embedding_raw = self._deserialize_embedding(row["embedding"]) if row["embedding"] else None
            embedding: Optional[List[float]] = cast(List[float], embedding_raw.tolist()) if embedding_raw is not None else None
            entities.append(
                Entity(
                    id=row["id"],
                    entity_type=row["entity_type"],
                    properties=properties,
                    embedding=embedding,
                )
            )

        return entities

    async def get_all_entities(self, entity_type: Optional[str] = None, limit: Optional[int] = None) -> List[Entity]:
        """Get all entities, optionally filtered by type"""
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        query = "SELECT id, entity_type, properties, embedding FROM graph_entities"
        params: List[Any] = []

        if entity_type:
            query += " WHERE entity_type = $1"
            params.append(entity_type)

        if limit:
            query += f" LIMIT ${len(params) + 1}"
            params.append(limit)

        if self._transaction_conn:
            conn = self._transaction_conn
            rows = await conn.fetch(query, *params)
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(query, *params)

        entities = []
        for row in rows:
            properties = json.loads(row["properties"]) if isinstance(row["properties"], str) else row["properties"]
            embedding_raw = self._deserialize_embedding(row["embedding"]) if row["embedding"] else None
            embedding: Optional[List[float]] = cast(List[float], embedding_raw.tolist()) if embedding_raw is not None else None
            entities.append(
                Entity(
                    id=row["id"],
                    entity_type=row["entity_type"],
                    properties=properties,
                    embedding=embedding,
                )
            )

        return entities

    async def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics"""
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        if self._transaction_conn:
            conn = self._transaction_conn
            entity_count = await conn.fetchval("SELECT COUNT(*) FROM graph_entities")
            relation_count = await conn.fetchval("SELECT COUNT(*) FROM graph_relations")
            entity_types = await conn.fetch("SELECT entity_type, COUNT(*) as count FROM graph_entities GROUP BY entity_type")
            relation_types = await conn.fetch("SELECT relation_type, COUNT(*) as count FROM graph_relations GROUP BY relation_type")
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                entity_count = await conn.fetchval("SELECT COUNT(*) FROM graph_entities")
                relation_count = await conn.fetchval("SELECT COUNT(*) FROM graph_relations")
                entity_types = await conn.fetch("SELECT entity_type, COUNT(*) as count FROM graph_entities GROUP BY entity_type")
                relation_types = await conn.fetch("SELECT relation_type, COUNT(*) as count FROM graph_relations GROUP BY relation_type")

        return {
            "entity_count": entity_count,
            "relation_count": relation_count,
            "entity_types": {row["entity_type"]: row["count"] for row in entity_types},
            "relation_types": {row["relation_type"]: row["count"] for row in relation_types},
            "backend": "postgresql",
            "pool_size": (f"{self.pool.get_size()}/{self.max_pool_size}" if self.pool else "0/0"),
        }

    # =========================================================================
    # Tier 2: Advanced Interface (PostgreSQL-optimized with recursive CTEs)
    # =========================================================================

    async def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 3,
        limit: Optional[int] = 10,
    ) -> List[Path]:
        """
        Find paths using WITH RECURSIVE CTE (PostgreSQL-optimized)

        This overrides the default implementation with an efficient
        recursive SQL query.
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        # Recursive CTE to find all paths
        query = """
            WITH RECURSIVE paths AS (
                -- Base case: direct connections
                SELECT
                    r.source_id,
                    r.target_id,
                    r.relation_type,
                    ARRAY[r.source_id] as path_nodes,
                    ARRAY[r.id] as path_relations,
                    1 as depth
                FROM graph_relations r
                WHERE r.source_id = $1

                UNION ALL

                -- Recursive case: extend paths
                SELECT
                    p.source_id,
                    r.target_id,
                    r.relation_type,
                    p.path_nodes || r.source_id,
                    p.path_relations || r.id,
                    p.depth + 1
                FROM paths p
                JOIN graph_relations r ON p.target_id = r.source_id
                WHERE p.depth < $3
                AND NOT (r.source_id = ANY(p.path_nodes))  -- Avoid cycles
            )
            SELECT DISTINCT
                path_nodes || target_id as nodes,
                path_relations as relations,
                depth
            FROM paths
            WHERE target_id = $2
            ORDER BY depth ASC
            LIMIT $4
        """

        if self._transaction_conn:
            conn = self._transaction_conn
            rows = await conn.fetch(query, source_id, target_id, max_depth, limit or 10)
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(query, source_id, target_id, max_depth, limit or 10)

        paths = []
        for row in rows:
            node_ids = row["nodes"]
            relation_ids = row["relations"]

            # Fetch entities and relations
            entities = []
            for node_id in node_ids:
                entity = await self.get_entity(node_id)
                if entity:
                    entities.append(entity)

            relations = []
            for rel_id in relation_ids:
                relation = await self.get_relation(rel_id)
                if relation:
                    relations.append(relation)

            if entities and relations:
                paths.append(Path(nodes=entities, edges=relations))

        return paths

    # =========================================================================
    # Helper methods
    # =========================================================================

    def _serialize_embedding(self, embedding) -> Optional[bytes]:
        """Serialize numpy array or list to bytes"""
        if embedding is None:
            return None
        # Handle both numpy array and list
        if isinstance(embedding, np.ndarray):
            return embedding.tobytes()
        elif isinstance(embedding, (list, tuple)):
            # Convert list to numpy array first
            arr = np.array(embedding, dtype=np.float32)
            return arr.tobytes()
        else:
            # Try to convert to numpy array
            arr = np.array(embedding, dtype=np.float32)
            return arr.tobytes()

    def _deserialize_embedding(self, data: bytes) -> Optional[np.ndarray]:
        """Deserialize bytes to numpy array"""
        if not data:
            return None
        return np.frombuffer(data, dtype=np.float32)
