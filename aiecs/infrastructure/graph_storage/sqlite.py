"""
SQLite Graph Storage Backend

Provides file-based persistent graph storage using SQLite.

Multi-tenancy Support:
- SHARED_SCHEMA mode: Single database with tenant_id column filtering
- SEPARATE_SCHEMA mode: Table prefixes per tenant (tenant_xxx_entities, tenant_xxx_relations)
- Global namespace for tenant_id=NULL (backward compatible)
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
from aiecs.infrastructure.graph_storage.tenant import (
    TenantContext,
    TenantIsolationMode,
    CrossTenantRelationError,
)


# SQL Schema for SQLite graph storage with multi-tenancy support
SCHEMA_SQL = """
-- Entities table with tenant_id for multi-tenancy
CREATE TABLE IF NOT EXISTS entities (
    id TEXT NOT NULL,
    tenant_id TEXT,              -- NULL for global namespace
    entity_type TEXT NOT NULL,
    properties TEXT NOT NULL,    -- JSON
    embedding BLOB,              -- Vector embedding (serialized)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, tenant_id)
);

-- Relations table with tenant_id for multi-tenancy
CREATE TABLE IF NOT EXISTS relations (
    id TEXT NOT NULL,
    tenant_id TEXT,              -- NULL for global namespace
    relation_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    properties TEXT NOT NULL,    -- JSON
    weight REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, tenant_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_tenant ON entities(tenant_id);
CREATE INDEX IF NOT EXISTS idx_entities_tenant_type ON entities(tenant_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(relation_type);
CREATE INDEX IF NOT EXISTS idx_relations_tenant ON relations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_id);
CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_id);
CREATE INDEX IF NOT EXISTS idx_relations_tenant_source ON relations(tenant_id, source_id);
CREATE INDEX IF NOT EXISTS idx_relations_tenant_target ON relations(tenant_id, target_id);
"""

# Migration SQL for adding tenant_id to existing databases
MIGRATION_ADD_TENANT_ID = """
-- Add tenant_id column to entities if not exists
ALTER TABLE entities ADD COLUMN tenant_id TEXT;

-- Add tenant_id column to relations if not exists  
ALTER TABLE relations ADD COLUMN tenant_id TEXT;

-- Create tenant indexes
CREATE INDEX IF NOT EXISTS idx_entities_tenant ON entities(tenant_id);
CREATE INDEX IF NOT EXISTS idx_entities_tenant_type ON entities(tenant_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_relations_tenant ON relations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_relations_tenant_source ON relations(tenant_id, source_id);
CREATE INDEX IF NOT EXISTS idx_relations_tenant_target ON relations(tenant_id, target_id);
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

    Multi-Tenancy Support:
    - SHARED_SCHEMA mode: Single database with tenant_id column filtering
    - SEPARATE_SCHEMA mode: Table prefixes per tenant
    - Global namespace for tenant_id=NULL (backward compatible)

    Example:
        ```python
        store = SQLiteGraphStore("knowledge_graph.db")
        await store.initialize()

        # Single-tenant usage (backward compatible)
        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await store.add_entity(entity)

        # Multi-tenant usage
        from aiecs.infrastructure.graph_storage.tenant import TenantContext
        context = TenantContext(tenant_id="acme-corp")
        await store.add_entity(entity, context=context)

        await store.close()
        ```
    """

    def __init__(self, db_path: str = ":memory:", isolation_mode: TenantIsolationMode = TenantIsolationMode.SHARED_SCHEMA, **kwargs):
        """
        Initialize SQLite graph store

        Args:
            db_path: Path to SQLite database file (":memory:" for in-memory)
            isolation_mode: Tenant isolation mode (SHARED_SCHEMA or SEPARATE_SCHEMA)
            **kwargs: Additional SQLite connection parameters
        """
        super().__init__()
        self.db_path = db_path
        self.isolation_mode = isolation_mode
        self.conn_kwargs = kwargs
        self.conn: Optional[aiosqlite.Connection] = None
        self._is_initialized = False
        self._in_transaction = False
        self._initialized_tenant_tables: set = set()  # Track created tenant tables for SEPARATE_SCHEMA

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

        # Create schema (for SHARED_SCHEMA mode or base tables)
        await self.conn.executescript(SCHEMA_SQL)
        await self.conn.commit()

        self._is_initialized = True
        self._initialized_tenant_tables = set()

    async def close(self):
        """Close database connection"""
        if self.conn:
            await self.conn.close()
            self.conn = None
        self._is_initialized = False
        self._initialized_tenant_tables = set()

    # =========================================================================
    # Multi-Tenancy Helpers
    # =========================================================================

    def _get_tenant_id(self, context: Optional[TenantContext]) -> Optional[str]:
        """Extract tenant_id from context, returns None for global namespace."""
        return context.tenant_id if context else None

    def _get_table_name(self, base_table: str, tenant_id: Optional[str]) -> str:
        """
        Get table name based on isolation mode.
        
        For SHARED_SCHEMA: Returns base table name (filtering done via WHERE clause)
        For SEPARATE_SCHEMA: Returns prefixed table name (tenant_xxx_entities)
        """
        if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA and tenant_id:
            # Sanitize tenant_id for use in table name (replace - with _)
            safe_tenant = tenant_id.replace("-", "_")
            return f"tenant_{safe_tenant}_{base_table}"
        return base_table

    async def _ensure_tenant_tables(self, tenant_id: str) -> None:
        """
        Ensure tenant-specific tables exist for SEPARATE_SCHEMA mode.
        
        Creates tables like tenant_xxx_entities and tenant_xxx_relations.
        """
        if self.isolation_mode != TenantIsolationMode.SEPARATE_SCHEMA:
            return
        
        if tenant_id in self._initialized_tenant_tables:
            return
        
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        safe_tenant = tenant_id.replace("-", "_")
        entities_table = f"tenant_{safe_tenant}_entities"
        relations_table = f"tenant_{safe_tenant}_relations"

        # Create tenant-specific tables
        tenant_schema = f"""
        CREATE TABLE IF NOT EXISTS {entities_table} (
            id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            properties TEXT NOT NULL,
            embedding BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS {relations_table} (
            id TEXT PRIMARY KEY,
            relation_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            properties TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_{safe_tenant}_entities_type ON {entities_table}(entity_type);
        CREATE INDEX IF NOT EXISTS idx_{safe_tenant}_relations_type ON {relations_table}(relation_type);
        CREATE INDEX IF NOT EXISTS idx_{safe_tenant}_relations_source ON {relations_table}(source_id);
        CREATE INDEX IF NOT EXISTS idx_{safe_tenant}_relations_target ON {relations_table}(target_id);
        """

        await self.conn.executescript(tenant_schema)
        await self.conn.commit()
        self._initialized_tenant_tables.add(tenant_id)

    def _build_tenant_filter(self, tenant_id: Optional[str], table_alias: str = "") -> Tuple[str, List]:
        """
        Build SQL WHERE clause for tenant filtering in SHARED_SCHEMA mode.
        
        Returns:
            Tuple of (WHERE clause fragment, parameters list)
        """
        prefix = f"{table_alias}." if table_alias else ""
        
        if tenant_id is None:
            return f"{prefix}tenant_id IS NULL", []
        else:
            return f"{prefix}tenant_id = ?", [tenant_id]

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

    async def add_entity(self, entity: Entity, context: Optional[TenantContext] = None) -> None:
        """
        Add entity to SQLite database
        
        Args:
            entity: Entity to add
            context: Optional tenant context for multi-tenant isolation
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        tenant_id = self._get_tenant_id(context)
        
        # Ensure tenant tables exist for SEPARATE_SCHEMA mode
        if tenant_id and self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA:
            await self._ensure_tenant_tables(tenant_id)
        
        table_name = self._get_table_name("entities", tenant_id)

        # Check if entity already exists (within tenant scope)
        if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA and tenant_id:
            cursor = await self.conn.execute(f"SELECT id FROM {table_name} WHERE id = ?", (entity.id,))
        else:
            tenant_filter, params = self._build_tenant_filter(tenant_id)
            cursor = await self.conn.execute(
                f"SELECT id FROM {table_name} WHERE id = ? AND {tenant_filter}",
                [entity.id] + params
            )
        
        existing = await cursor.fetchone()
        if existing:
            raise ValueError(f"Entity with ID '{entity.id}' already exists")

        # Set tenant_id on entity if context provided
        if tenant_id is not None and entity.tenant_id is None:
            entity.tenant_id = tenant_id

        # Serialize data
        properties_json = json.dumps(entity.properties)
        embedding_blob = self._serialize_embedding(entity.embedding) if entity.embedding else None

        # Insert entity
        if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA and tenant_id:
            await self.conn.execute(
                f"""
                INSERT INTO {table_name} (id, entity_type, properties, embedding)
                VALUES (?, ?, ?, ?)
                """,
                (entity.id, entity.entity_type, properties_json, embedding_blob),
            )
        else:
            await self.conn.execute(
                f"""
                INSERT INTO {table_name} (id, tenant_id, entity_type, properties, embedding)
                VALUES (?, ?, ?, ?, ?)
                """,
                (entity.id, tenant_id, entity.entity_type, properties_json, embedding_blob),
            )
        
        if not self._in_transaction:
            await self.conn.commit()

    async def get_entity(self, entity_id: str, context: Optional[TenantContext] = None) -> Optional[Entity]:
        """
        Get entity from SQLite database
        
        Args:
            entity_id: Entity ID to retrieve
            context: Optional tenant context for multi-tenant isolation
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        tenant_id = self._get_tenant_id(context)
        table_name = self._get_table_name("entities", tenant_id)

        if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA and tenant_id:
            # SEPARATE_SCHEMA: No tenant_id column in tenant-specific tables
            cursor = await self.conn.execute(
                f"""
                SELECT id, entity_type, properties, embedding
                FROM {table_name}
                WHERE id = ?
                """,
                (entity_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_entity(tuple(row), tenant_id=tenant_id)
        else:
            # SHARED_SCHEMA: Filter by tenant_id column
            tenant_filter, params = self._build_tenant_filter(tenant_id)
            cursor = await self.conn.execute(
                f"""
                SELECT id, tenant_id, entity_type, properties, embedding
                FROM {table_name}
                WHERE id = ? AND {tenant_filter}
                """,
                [entity_id] + params,
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_entity_with_tenant(tuple(row))

    async def update_entity(self, entity: Entity, context: Optional[TenantContext] = None) -> Entity:
        """
        Update entity in SQLite database
        
        Args:
            entity: Entity to update
            context: Optional tenant context for multi-tenant isolation
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        tenant_id = self._get_tenant_id(context)
        table_name = self._get_table_name("entities", tenant_id)

        # Check if entity exists
        existing = await self.get_entity(entity.id, context=context)
        if not existing:
            raise ValueError(f"Entity with ID '{entity.id}' does not exist")

        # Serialize data
        properties_json = json.dumps(entity.properties)
        embedding_blob = self._serialize_embedding(entity.embedding) if entity.embedding else None

        # Update entity
        if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA and tenant_id:
            await self.conn.execute(
                f"""
                UPDATE {table_name}
                SET entity_type = ?, properties = ?, embedding = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (entity.entity_type, properties_json, embedding_blob, entity.id),
            )
        else:
            tenant_filter, params = self._build_tenant_filter(tenant_id)
            await self.conn.execute(
                f"""
                UPDATE {table_name}
                SET entity_type = ?, properties = ?, embedding = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND {tenant_filter}
                """,
                [entity.entity_type, properties_json, embedding_blob, entity.id] + params,
            )
        
        if not self._in_transaction:
            await self.conn.commit()

        return entity

    async def delete_entity(self, entity_id: str, context: Optional[TenantContext] = None):
        """
        Delete entity and its relations from SQLite database
        
        Args:
            entity_id: Entity ID to delete
            context: Optional tenant context for multi-tenant isolation
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        tenant_id = self._get_tenant_id(context)
        entities_table = self._get_table_name("entities", tenant_id)
        relations_table = self._get_table_name("relations", tenant_id)

        if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA and tenant_id:
            # Delete relations first (no foreign key in SEPARATE_SCHEMA)
            await self.conn.execute(
                f"DELETE FROM {relations_table} WHERE source_id = ? OR target_id = ?",
                (entity_id, entity_id)
            )
            await self.conn.execute(f"DELETE FROM {entities_table} WHERE id = ?", (entity_id,))
        else:
            tenant_filter, params = self._build_tenant_filter(tenant_id)
            # Delete relations first
            await self.conn.execute(
                f"DELETE FROM {relations_table} WHERE (source_id = ? OR target_id = ?) AND {tenant_filter}",
                [entity_id, entity_id] + params
            )
            await self.conn.execute(
                f"DELETE FROM {entities_table} WHERE id = ? AND {tenant_filter}",
                [entity_id] + params
            )
        
        if not self._in_transaction:
            await self.conn.commit()

    async def add_relation(self, relation: Relation, context: Optional[TenantContext] = None) -> None:
        """
        Add relation to SQLite database
        
        Args:
            relation: Relation to add
            context: Optional tenant context for multi-tenant isolation
            
        Raises:
            CrossTenantRelationError: If source and target entities belong to different tenants
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        tenant_id = self._get_tenant_id(context)
        
        # Ensure tenant tables exist for SEPARATE_SCHEMA mode
        if tenant_id and self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA:
            await self._ensure_tenant_tables(tenant_id)
        
        table_name = self._get_table_name("relations", tenant_id)

        # Check if relation already exists (within tenant scope)
        if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA and tenant_id:
            cursor = await self.conn.execute(f"SELECT id FROM {table_name} WHERE id = ?", (relation.id,))
        else:
            tenant_filter, params = self._build_tenant_filter(tenant_id)
            cursor = await self.conn.execute(
                f"SELECT id FROM {table_name} WHERE id = ? AND {tenant_filter}",
                [relation.id] + params
            )
        
        existing = await cursor.fetchone()
        if existing:
            raise ValueError(f"Relation with ID '{relation.id}' already exists")

        # Check if entities exist within tenant scope
        source_entity = await self.get_entity(relation.source_id, context=context)
        target_entity = await self.get_entity(relation.target_id, context=context)
        
        if not source_entity:
            raise ValueError(f"Source entity '{relation.source_id}' does not exist")
        if not target_entity:
            raise ValueError(f"Target entity '{relation.target_id}' does not exist")

        # Enforce same-tenant constraint
        if tenant_id is not None:
            source_tenant = source_entity.tenant_id
            target_tenant = target_entity.tenant_id
            if source_tenant != target_tenant:
                raise CrossTenantRelationError(source_tenant, target_tenant)

        # Set tenant_id on relation if context provided
        if tenant_id is not None and relation.tenant_id is None:
            relation.tenant_id = tenant_id

        # Serialize data
        properties_json = json.dumps(relation.properties)

        # Insert relation
        if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA and tenant_id:
            await self.conn.execute(
                f"""
                INSERT INTO {table_name} (id, relation_type, source_id, target_id, properties, weight)
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
        else:
            await self.conn.execute(
                f"""
                INSERT INTO {table_name} (id, tenant_id, relation_type, source_id, target_id, properties, weight)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    relation.id,
                    tenant_id,
                    relation.relation_type,
                    relation.source_id,
                    relation.target_id,
                    properties_json,
                    relation.weight,
                ),
            )
        
        if not self._in_transaction:
            await self.conn.commit()

    async def get_relation(self, relation_id: str, context: Optional[TenantContext] = None) -> Optional[Relation]:
        """
        Get relation from SQLite database
        
        Args:
            relation_id: Relation ID to retrieve
            context: Optional tenant context for multi-tenant isolation
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        tenant_id = self._get_tenant_id(context)
        table_name = self._get_table_name("relations", tenant_id)

        if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA and tenant_id:
            cursor = await self.conn.execute(
                f"""
                SELECT id, relation_type, source_id, target_id, properties, weight
                FROM {table_name}
                WHERE id = ?
                """,
                (relation_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_relation(tuple(row), tenant_id=tenant_id)
        else:
            tenant_filter, params = self._build_tenant_filter(tenant_id)
            cursor = await self.conn.execute(
                f"""
                SELECT id, tenant_id, relation_type, source_id, target_id, properties, weight
                FROM {table_name}
                WHERE id = ? AND {tenant_filter}
                """,
                [relation_id] + params,
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_relation_with_tenant(tuple(row))

    async def update_relation(self, relation: Relation, context: Optional[TenantContext] = None) -> Relation:
        """
        Update relation in SQLite database
        
        Args:
            relation: Relation to update
            context: Optional tenant context for multi-tenant isolation
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        tenant_id = self._get_tenant_id(context)
        table_name = self._get_table_name("relations", tenant_id)

        # Check if relation exists
        existing = await self.get_relation(relation.id, context=context)
        if not existing:
            raise ValueError(f"Relation with ID '{relation.id}' does not exist")

        # Serialize data
        properties_json = json.dumps(relation.properties)

        # Update relation
        if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA and tenant_id:
            await self.conn.execute(
                f"""
                UPDATE {table_name}
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
        else:
            tenant_filter, params = self._build_tenant_filter(tenant_id)
            await self.conn.execute(
                f"""
                UPDATE {table_name}
                SET relation_type = ?, source_id = ?, target_id = ?, properties = ?,
                    weight = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND {tenant_filter}
                """,
                [
                    relation.relation_type,
                    relation.source_id,
                    relation.target_id,
                    properties_json,
                    relation.weight,
                    relation.id,
                ] + params,
            )
        
        if not self._in_transaction:
            await self.conn.commit()

        return relation

    async def delete_relation(self, relation_id: str, context: Optional[TenantContext] = None):
        """
        Delete relation from SQLite database
        
        Args:
            relation_id: Relation ID to delete
            context: Optional tenant context for multi-tenant isolation
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        tenant_id = self._get_tenant_id(context)
        table_name = self._get_table_name("relations", tenant_id)

        if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA and tenant_id:
            await self.conn.execute(f"DELETE FROM {table_name} WHERE id = ?", (relation_id,))
        else:
            tenant_filter, params = self._build_tenant_filter(tenant_id)
            await self.conn.execute(
                f"DELETE FROM {table_name} WHERE id = ? AND {tenant_filter}",
                [relation_id] + params
            )
        
        if not self._in_transaction:
            await self.conn.commit()

    async def get_neighbors(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        direction: str = "outgoing",
        context: Optional[TenantContext] = None,
    ) -> List[Entity]:
        """
        Get neighboring entities connected by relations

        Implements the base GraphStore interface.

        Args:
            entity_id: ID of entity to get neighbors for
            relation_type: Optional filter by relation type
            direction: "outgoing", "incoming", or "both"
            context: Optional tenant context for multi-tenant isolation

        Returns:
            List of neighboring entities
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        tenant_id = self._get_tenant_id(context)
        entities_table = self._get_table_name("entities", tenant_id)
        relations_table = self._get_table_name("relations", tenant_id)

        neighbors = []

        # Build WHERE clause for relation type
        type_filter = ""
        if relation_type:
            type_filter = "AND r.relation_type = ?"

        if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA and tenant_id:
            # SEPARATE_SCHEMA: No tenant filtering needed (table is tenant-specific)
            params = [entity_id]
            if relation_type:
                params.append(relation_type)

            # Outgoing relations
            if direction in ["outgoing", "both"]:
                query = f"""
                    SELECT e.id, e.entity_type, e.properties, e.embedding
                    FROM {relations_table} r
                    JOIN {entities_table} e ON r.target_id = e.id
                    WHERE r.source_id = ? {type_filter}
                """

                cursor = await self.conn.execute(query, params)
                rows = await cursor.fetchall()

                for row in rows:
                    entity = self._row_to_entity(tuple(row), tenant_id=tenant_id)
                    neighbors.append(entity)

            # Incoming relations
            if direction in ["incoming", "both"]:
                params_incoming = [entity_id]
                if relation_type:
                    params_incoming.append(relation_type)

                query = f"""
                    SELECT e.id, e.entity_type, e.properties, e.embedding
                    FROM {relations_table} r
                    JOIN {entities_table} e ON r.source_id = e.id
                    WHERE r.target_id = ? {type_filter}
                """

                cursor = await self.conn.execute(query, params_incoming)
                rows = await cursor.fetchall()

                for row in rows:
                    entity = self._row_to_entity(tuple(row), tenant_id=tenant_id)
                    neighbors.append(entity)
        else:
            # SHARED_SCHEMA: Filter by tenant_id
            tenant_filter_r, tenant_params = self._build_tenant_filter(tenant_id, "r")
            tenant_filter_e, tenant_params_e = self._build_tenant_filter(tenant_id, "e")

            # Outgoing relations
            if direction in ["outgoing", "both"]:
                # Parameter order must match query: JOIN condition (e.tenant), WHERE source_id, [type], r.tenant
                params = tenant_params_e + [entity_id]
                if relation_type:
                    params.append(relation_type)
                params.extend(tenant_params)

                query = f"""
                    SELECT e.id, e.tenant_id, e.entity_type, e.properties, e.embedding
                    FROM {relations_table} r
                    JOIN {entities_table} e ON r.target_id = e.id AND {tenant_filter_e}
                    WHERE r.source_id = ? {type_filter} AND {tenant_filter_r}
                """

                cursor = await self.conn.execute(query, params)
                rows = await cursor.fetchall()

                for row in rows:
                    entity = self._row_to_entity_with_tenant(tuple(row))
                    neighbors.append(entity)

            # Incoming relations
            if direction in ["incoming", "both"]:
                # Parameter order must match query: JOIN condition (e.tenant), WHERE target_id, [type], r.tenant
                params_incoming = tenant_params_e + [entity_id]
                if relation_type:
                    params_incoming.append(relation_type)
                params_incoming.extend(tenant_params)

                query = f"""
                    SELECT e.id, e.tenant_id, e.entity_type, e.properties, e.embedding
                    FROM {relations_table} r
                    JOIN {entities_table} e ON r.source_id = e.id AND {tenant_filter_e}
                    WHERE r.target_id = ? {type_filter} AND {tenant_filter_r}
                """

                cursor = await self.conn.execute(query, params_incoming)
                rows = await cursor.fetchall()

                for row in rows:
                    entity = self._row_to_entity_with_tenant(tuple(row))
                    neighbors.append(entity)

        return neighbors

    # =========================================================================
    # Tier 2: Advanced Interface (SQL-optimized overrides)
    # =========================================================================

    async def get_all_entities(
        self,
        entity_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        context: Optional[TenantContext] = None,
    ) -> List[Entity]:
        """
        Get all entities in the graph store

        SQL-optimized implementation that uses efficient queries with filtering
        and pagination.

        Args:
            entity_type: Optional filter by entity type
            limit: Optional maximum number of entities to return
            offset: Number of entities to skip (for pagination)
            context: Optional tenant context for multi-tenant isolation

        Returns:
            List of entities matching the criteria
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        tenant_id = self._get_tenant_id(context)
        table_name = self._get_table_name("entities", tenant_id)

        # Build query with filters
        conditions = []
        params = []

        if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA and tenant_id:
            # SEPARATE_SCHEMA: No tenant_id column, tenant filtering via table_name
            if entity_type:
                conditions.append("entity_type = ?")
                params.append(entity_type)
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            # Build LIMIT and OFFSET clauses
            limit_clause = ""
            if limit is not None and offset > 0:
                limit_clause = f"LIMIT {limit} OFFSET {offset}"
            elif limit is not None:
                limit_clause = f"LIMIT {limit}"
            elif offset > 0:
                limit_clause = f"OFFSET {offset}"
            
            # Execute query
            query = f"""
                SELECT id, entity_type, properties, embedding
                FROM {table_name}
                {where_clause}
                {limit_clause}
            """
            
            cursor = await self.conn.execute(query, params)
            rows = await cursor.fetchall()
            
            # Convert rows to entities
            entities = []
            for row in rows:
                entity = self._row_to_entity(tuple(row), tenant_id=tenant_id)
                entities.append(entity)
        else:
            # SHARED_SCHEMA: Filter by tenant_id column
            tenant_filter, tenant_params = self._build_tenant_filter(tenant_id)
            if tenant_filter:
                conditions.append(tenant_filter)
                params.extend(tenant_params)
            
            # Entity type filtering
            if entity_type:
                conditions.append("entity_type = ?")
                params.append(entity_type)
            
            # Build WHERE clause
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            # Build LIMIT and OFFSET clauses
            limit_clause = ""
            if limit is not None and offset > 0:
                limit_clause = f"LIMIT {limit} OFFSET {offset}"
            elif limit is not None:
                limit_clause = f"LIMIT {limit}"
            elif offset > 0:
                limit_clause = f"OFFSET {offset}"
            
            # Execute query
            query = f"""
                SELECT id, tenant_id, entity_type, properties, embedding
                FROM {table_name}
                {where_clause}
                {limit_clause}
            """
            
            cursor = await self.conn.execute(query, params)
            rows = await cursor.fetchall()
            
            # Convert rows to entities
            entities = []
            for row in rows:
                entity = self._row_to_entity_with_tenant(tuple(row))
                entities.append(entity)

        return entities

    async def vector_search(
        self,
        query_embedding: List[float],
        entity_type: Optional[str] = None,
        max_results: int = 10,
        score_threshold: float = 0.0,
        context: Optional[TenantContext] = None,
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
            context: Optional tenant context for multi-tenant isolation

        Returns:
            List of (entity, similarity_score) tuples, sorted descending
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        if not query_embedding:
            raise ValueError("Query embedding cannot be empty")

        tenant_id = self._get_tenant_id(context)
        table_name = self._get_table_name("entities", tenant_id)

        if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA and tenant_id:
            # SEPARATE_SCHEMA: No tenant filtering needed
            type_filter = "WHERE entity_type = ?" if entity_type else ""
            params = [entity_type] if entity_type else []

            query = f"""
                SELECT id, entity_type, properties, embedding
                FROM {table_name}
                {type_filter}
            """

            cursor = await self.conn.execute(query, params)
            rows = await cursor.fetchall()

            # Compute similarities
            scored_entities = []
            for row in rows:
                entity = self._row_to_entity(tuple(row), tenant_id=tenant_id)

                if not entity.embedding:
                    continue

                similarity = self._cosine_similarity(query_embedding, entity.embedding)
                if similarity >= score_threshold:
                    scored_entities.append((entity, similarity))
        else:
            # SHARED_SCHEMA: Filter by tenant_id
            tenant_filter, tenant_params = self._build_tenant_filter(tenant_id)
            
            if entity_type:
                where_clause = f"WHERE {tenant_filter} AND entity_type = ?"
                params = tenant_params + [entity_type]
            else:
                where_clause = f"WHERE {tenant_filter}"
                params = tenant_params

            query = f"""
                SELECT id, tenant_id, entity_type, properties, embedding
                FROM {table_name}
                {where_clause}
            """

            cursor = await self.conn.execute(query, params)
            rows = await cursor.fetchall()

            # Compute similarities
            scored_entities = []
            for row in rows:
                entity = self._row_to_entity_with_tenant(tuple(row))

                if not entity.embedding:
                    continue

                similarity = self._cosine_similarity(query_embedding, entity.embedding)
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
        context: Optional[TenantContext] = None,
    ) -> List[Path]:
        """
        SQL-optimized traversal using recursive CTE

        This overrides the default Tier 2 implementation for better performance.
        Uses recursive CTEs in SQLite for efficient graph traversal.
        
        Args:
            start_entity_id: Starting entity ID
            relation_type: Optional filter by relation type
            max_depth: Maximum traversal depth
            max_results: Maximum number of paths to return
            context: Optional tenant context for multi-tenant isolation
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        # For SQLite, we'll use the default implementation from base class
        # which uses BFS with get_neighbors(). While recursive CTEs are powerful,
        # building full Path objects with them is complex. The default is sufficient.
        # Backends with native graph query languages (e.g., Neo4j with Cypher)
        # should override this for better performance.
        return await self._default_traverse_bfs(start_entity_id, relation_type, max_depth, max_results, context)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _row_to_entity(self, row: tuple, tenant_id: Optional[str] = None) -> Entity:
        """Convert database row to Entity object (for SEPARATE_SCHEMA without tenant_id column)"""
        entity_id, entity_type, properties_json, embedding_blob = row

        properties = json.loads(properties_json)
        embedding = self._deserialize_embedding(embedding_blob) if embedding_blob else None

        return Entity(
            id=entity_id,
            entity_type=entity_type,
            properties=properties,
            embedding=embedding,
            tenant_id=tenant_id,
        )

    def _row_to_entity_with_tenant(self, row: tuple) -> Entity:
        """Convert database row to Entity object (for SHARED_SCHEMA with tenant_id column)"""
        entity_id, tenant_id, entity_type, properties_json, embedding_blob = row

        properties = json.loads(properties_json)
        embedding = self._deserialize_embedding(embedding_blob) if embedding_blob else None

        return Entity(
            id=entity_id,
            entity_type=entity_type,
            properties=properties,
            embedding=embedding,
            tenant_id=tenant_id,
        )

    def _row_to_relation(self, row: tuple, tenant_id: Optional[str] = None) -> Relation:
        """Convert database row to Relation object (for SEPARATE_SCHEMA without tenant_id column)"""
        rel_id, rel_type, source_id, target_id, properties_json, weight = row

        properties = json.loads(properties_json)

        return Relation(
            id=rel_id,
            relation_type=rel_type,
            source_id=source_id,
            target_id=target_id,
            properties=properties,
            weight=weight,
            tenant_id=tenant_id,
        )

    def _row_to_relation_with_tenant(self, row: tuple) -> Relation:
        """Convert database row to Relation object (for SHARED_SCHEMA with tenant_id column)"""
        rel_id, tenant_id, rel_type, source_id, target_id, properties_json, weight = row

        properties = json.loads(properties_json)

        return Relation(
            id=rel_id,
            relation_type=rel_type,
            source_id=source_id,
            target_id=target_id,
            properties=properties,
            weight=weight,
            tenant_id=tenant_id,
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

    async def get_stats(self, context: Optional[TenantContext] = None) -> Dict[str, Any]:
        """
        Get statistics about the SQLite graph store
        
        Args:
            context: Optional tenant context for tenant-scoped stats
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        tenant_id = self._get_tenant_id(context)
        entities_table = self._get_table_name("entities", tenant_id)
        relations_table = self._get_table_name("relations", tenant_id)

        if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA and tenant_id:
            # Check if tenant tables exist
            cursor = await self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (entities_table,)
            )
            table_exists = await cursor.fetchone()
            
            if not table_exists:
                entity_count = 0
                relation_count = 0
            else:
                cursor = await self.conn.execute(f"SELECT COUNT(*) FROM {entities_table}")
                entity_row = await cursor.fetchone()
                entity_count = entity_row[0] if entity_row else 0

                cursor = await self.conn.execute(f"SELECT COUNT(*) FROM {relations_table}")
                relation_row = await cursor.fetchone()
                relation_count = relation_row[0] if relation_row else 0
        else:
            tenant_filter, params = self._build_tenant_filter(tenant_id)
            
            cursor = await self.conn.execute(
                f"SELECT COUNT(*) FROM {entities_table} WHERE {tenant_filter}",
                params
            )
            entity_row = await cursor.fetchone()
            entity_count = entity_row[0] if entity_row else 0

            cursor = await self.conn.execute(
                f"SELECT COUNT(*) FROM {relations_table} WHERE {tenant_filter}",
                params
            )
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
            "isolation_mode": self.isolation_mode.value,
            "tenant_id": tenant_id,
        }

    async def clear(self, context: Optional[TenantContext] = None):
        """
        Clear data from SQLite database
        
        Args:
            context: Optional tenant context for multi-tenant isolation.
                    If provided, clears only data for the specified tenant.
                    If None, clears all data.
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        tenant_id = self._get_tenant_id(context)

        if tenant_id is None:
            # Clear all data (global and all tenants)
            await self.conn.execute("DELETE FROM relations")
            await self.conn.execute("DELETE FROM entities")
            
            # Drop all tenant-specific tables for SEPARATE_SCHEMA
            if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA:
                cursor = await self.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'tenant_%'"
                )
                tables = await cursor.fetchall()
                for (table_name,) in tables:
                    await self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                self._initialized_tenant_tables.clear()
        else:
            # Clear tenant-specific data
            if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA:
                entities_table = self._get_table_name("entities", tenant_id)
                relations_table = self._get_table_name("relations", tenant_id)
                
                # Drop tenant tables
                await self.conn.execute(f"DROP TABLE IF EXISTS {relations_table}")
                await self.conn.execute(f"DROP TABLE IF EXISTS {entities_table}")
                self._initialized_tenant_tables.discard(tenant_id)
            else:
                # Delete from shared tables with tenant filter
                tenant_filter, params = self._build_tenant_filter(tenant_id)
                await self.conn.execute(
                    f"DELETE FROM relations WHERE {tenant_filter}",
                    params
                )
                await self.conn.execute(
                    f"DELETE FROM entities WHERE {tenant_filter}",
                    params
                )
        
        if not self._in_transaction:
            await self.conn.commit()

    async def migrate_add_tenant_id(self):
        """
        Migration script to add tenant_id column to existing databases.
        
        This should be run once when upgrading an existing database to support multi-tenancy.
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        # Check if tenant_id column already exists
        cursor = await self.conn.execute("PRAGMA table_info(entities)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if "tenant_id" in column_names:
            return  # Migration already applied

        # Apply migration
        try:
            await self.conn.execute("ALTER TABLE entities ADD COLUMN tenant_id TEXT")
            await self.conn.execute("ALTER TABLE relations ADD COLUMN tenant_id TEXT")
            
            # Create tenant indexes
            await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_tenant ON entities(tenant_id)")
            await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_tenant_type ON entities(tenant_id, entity_type)")
            await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_tenant ON relations(tenant_id)")
            await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_tenant_source ON relations(tenant_id, source_id)")
            await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_tenant_target ON relations(tenant_id, target_id)")
            
            await self.conn.commit()
        except Exception as e:
            await self.conn.rollback()
            raise RuntimeError(f"Migration failed: {e}")
