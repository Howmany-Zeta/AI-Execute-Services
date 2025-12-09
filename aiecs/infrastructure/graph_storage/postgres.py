"""
PostgreSQL Graph Storage Backend

Provides production-grade graph storage using PostgreSQL with:
- Connection pooling via asyncpg
- Transaction support
- Recursive CTEs for efficient graph traversal
- Optional pgvector support for vector similarity search

Multi-tenancy Support:
- SHARED_SCHEMA mode: Single schema with tenant_id column + optional RLS
- SEPARATE_SCHEMA mode: PostgreSQL schemas per tenant (CREATE SCHEMA tenant_xxx)
- Global namespace for tenant_id=NULL (backward compatible)
"""

import json
import asyncpg  # type: ignore[import-untyped]
import logging
from typing import Any, Dict, List, Optional, Tuple, cast
from contextlib import asynccontextmanager
import numpy as np

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.path import Path
from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.infrastructure.graph_storage.tenant import (
    TenantContext,
    TenantIsolationMode,
    CrossTenantRelationError,
)
from aiecs.config.config import get_settings

logger = logging.getLogger(__name__)


# PostgreSQL Schema for graph storage with multi-tenancy support
# Note: For existing databases, run MIGRATION_SQL first to add tenant_id columns
# Uses empty string '' as default for tenant_id to allow proper composite primary key
SCHEMA_SQL = """
-- Entities table with tenant_id for multi-tenancy
-- tenant_id = '' (empty string) for global namespace
CREATE TABLE IF NOT EXISTS graph_entities (
    id TEXT NOT NULL,
    tenant_id TEXT NOT NULL DEFAULT '',       -- Empty string for global namespace
    entity_type TEXT NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding BYTEA,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, tenant_id)
);

-- Relations table with tenant_id for multi-tenancy  
CREATE TABLE IF NOT EXISTS graph_relations (
    id TEXT NOT NULL,
    tenant_id TEXT NOT NULL DEFAULT '',       -- Empty string for global namespace
    relation_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    weight REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, tenant_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_graph_entities_type ON graph_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_graph_entities_tenant ON graph_entities(tenant_id);
CREATE INDEX IF NOT EXISTS idx_graph_entities_tenant_type ON graph_entities(tenant_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_graph_entities_properties ON graph_entities USING GIN(properties);
CREATE INDEX IF NOT EXISTS idx_graph_relations_type ON graph_relations(relation_type);
CREATE INDEX IF NOT EXISTS idx_graph_relations_tenant ON graph_relations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_graph_relations_source ON graph_relations(source_id);
CREATE INDEX IF NOT EXISTS idx_graph_relations_target ON graph_relations(target_id);
CREATE INDEX IF NOT EXISTS idx_graph_relations_tenant_source ON graph_relations(tenant_id, source_id);
CREATE INDEX IF NOT EXISTS idx_graph_relations_tenant_target ON graph_relations(tenant_id, target_id);
CREATE INDEX IF NOT EXISTS idx_graph_relations_properties ON graph_relations USING GIN(properties);

-- Optional: Add pgvector extension support (if available)
-- CREATE EXTENSION IF NOT EXISTS vector;
-- ALTER TABLE graph_entities ADD COLUMN IF NOT EXISTS embedding_vector vector(1536);
-- CREATE INDEX IF NOT EXISTS idx_graph_entities_embedding ON graph_entities USING ivfflat (embedding_vector vector_cosine_ops);
"""

# Migration SQL for existing databases (adds tenant_id columns if they don't exist)
MIGRATION_SQL = """
-- Add tenant_id column to entities if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'graph_entities' AND column_name = 'tenant_id'
    ) THEN
        -- Add tenant_id column with empty string default
        ALTER TABLE graph_entities ADD COLUMN tenant_id TEXT NOT NULL DEFAULT '';
        
        -- Drop old primary key if exists
        ALTER TABLE graph_entities DROP CONSTRAINT IF EXISTS graph_entities_pkey;
        
        -- Create new composite primary key
        ALTER TABLE graph_entities ADD PRIMARY KEY (id, tenant_id);
        
        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_graph_entities_tenant ON graph_entities(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_graph_entities_tenant_type ON graph_entities(tenant_id, entity_type);
    END IF;
END $$;

-- Add tenant_id column to relations if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'graph_relations' AND column_name = 'tenant_id'
    ) THEN
        -- Add tenant_id column with empty string default
        ALTER TABLE graph_relations ADD COLUMN tenant_id TEXT NOT NULL DEFAULT '';
        
        -- Drop old primary key if exists
        ALTER TABLE graph_relations DROP CONSTRAINT IF EXISTS graph_relations_pkey;
        
        -- Create new composite primary key
        ALTER TABLE graph_relations ADD PRIMARY KEY (id, tenant_id);
        
        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_graph_relations_tenant ON graph_relations(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_graph_relations_tenant_source ON graph_relations(tenant_id, source_id);
        CREATE INDEX IF NOT EXISTS idx_graph_relations_tenant_target ON graph_relations(tenant_id, target_id);
    END IF;
END $$;
"""

# RLS (Row-Level Security) policies for SHARED_SCHEMA mode
RLS_SETUP_SQL = """
-- Enable RLS on tables
ALTER TABLE graph_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_relations ENABLE ROW LEVEL SECURITY;

-- Force RLS even for table owners (important for superuser/owner connections)
ALTER TABLE graph_entities FORCE ROW LEVEL SECURITY;
ALTER TABLE graph_relations FORCE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS tenant_isolation_entities ON graph_entities;
DROP POLICY IF EXISTS tenant_isolation_relations ON graph_relations;

-- Create RLS policies
-- Note: Uses current_setting('app.current_tenant_id', true) which returns empty string if not set
-- Empty string ('') represents the global namespace
CREATE POLICY tenant_isolation_entities ON graph_entities
    USING (
        tenant_id = '' OR 
        tenant_id = COALESCE(current_setting('app.current_tenant_id', true), '')
    );

CREATE POLICY tenant_isolation_relations ON graph_relations
    USING (
        tenant_id = '' OR
        tenant_id = COALESCE(current_setting('app.current_tenant_id', true), '')
    );
"""

# Schema template for SEPARATE_SCHEMA mode
TENANT_SCHEMA_SQL = """
-- Create tenant schema
CREATE SCHEMA IF NOT EXISTS {schema_name};

-- Entities table in tenant schema
CREATE TABLE IF NOT EXISTS {schema_name}.graph_entities (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    properties JSONB NOT NULL DEFAULT '{{}}'::jsonb,
    embedding BYTEA,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Relations table in tenant schema
CREATE TABLE IF NOT EXISTS {schema_name}.graph_relations (
    id TEXT PRIMARY KEY,
    relation_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    properties JSONB NOT NULL DEFAULT '{{}}'::jsonb,
    weight REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_{schema_name}_entities_type ON {schema_name}.graph_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_{schema_name}_relations_type ON {schema_name}.graph_relations(relation_type);
CREATE INDEX IF NOT EXISTS idx_{schema_name}_relations_source ON {schema_name}.graph_relations(source_id);
CREATE INDEX IF NOT EXISTS idx_{schema_name}_relations_target ON {schema_name}.graph_relations(target_id);
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

    Multi-Tenancy Support:
    - SHARED_SCHEMA mode: Single schema with tenant_id column + optional RLS
    - SEPARATE_SCHEMA mode: PostgreSQL schemas per tenant (CREATE SCHEMA tenant_xxx)
    - Global namespace for tenant_id=NULL (backward compatible)
    - Row-Level Security (RLS) for automatic tenant filtering

    Example:
        ```python
        from aiecs.infrastructure.graph_storage import PostgresGraphStore

        # Using config from settings
        store = PostgresGraphStore()
        await store.initialize()

        # Multi-tenant with RLS
        store = PostgresGraphStore(
            isolation_mode=TenantIsolationMode.SHARED_SCHEMA,
            enable_rls=True
        )
        await store.initialize()

        # Multi-tenant usage
        from aiecs.infrastructure.graph_storage.tenant import TenantContext
        context = TenantContext(tenant_id="acme-corp")
        await store.add_entity(entity, context=context)

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
        isolation_mode: TenantIsolationMode = TenantIsolationMode.SHARED_SCHEMA,
        enable_rls: bool = False,
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
            isolation_mode: Tenant isolation mode (SHARED_SCHEMA or SEPARATE_SCHEMA)
            enable_rls: Enable Row-Level Security for SHARED_SCHEMA mode
            pool: Optional existing asyncpg pool to reuse (from DatabaseManager)
            database_manager: Optional DatabaseManager instance to reuse its pool
            **kwargs: Additional asyncpg connection parameters
        """
        super().__init__()
        
        # Multi-tenancy configuration
        self.isolation_mode = isolation_mode
        self.enable_rls = enable_rls
        self._initialized_tenant_schemas: set = set()  # Track created tenant schemas

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

                # Check if tables exist and need migration
                tables_exist = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name = 'graph_entities'
                    )
                    """
                )
                
                if tables_exist:
                    # Run migration for existing databases to add tenant_id
                    try:
                        await conn.execute(MIGRATION_SQL)
                        logger.info("Database migration for multi-tenancy completed")
                    except Exception as e:
                        logger.warning(f"Migration may have already been applied: {e}")
                else:
                    # Execute schema creation for new databases
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

                # Set up RLS if enabled for SHARED_SCHEMA mode
                if self.enable_rls and self.isolation_mode == TenantIsolationMode.SHARED_SCHEMA:
                    try:
                        await conn.execute(RLS_SETUP_SQL)
                        logger.info("Row-Level Security (RLS) policies enabled")
                    except Exception as e:
                        logger.warning(f"Failed to set up RLS: {e}. Continuing without RLS.")
                        self.enable_rls = False

            self._is_initialized = True
            self._initialized_tenant_schemas = set()
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
        self._initialized_tenant_schemas = set()

    # =========================================================================
    # Multi-Tenancy Helpers
    # =========================================================================

    def _get_tenant_id(self, context: Optional[TenantContext]) -> str:
        """Extract tenant_id from context, returns empty string for global namespace."""
        return context.tenant_id if context and context.tenant_id else ""

    def _get_schema_name(self, tenant_id: Optional[str]) -> str:
        """
        Get schema name for SEPARATE_SCHEMA mode.
        
        Returns 'public' for global namespace or 'tenant_xxx' for tenants.
        """
        if tenant_id is None:
            return "public"
        # Sanitize tenant_id for use in schema name
        safe_tenant = tenant_id.replace("-", "_")
        return f"tenant_{safe_tenant}"

    async def _ensure_tenant_schema(self, conn: asyncpg.Connection, tenant_id: str) -> None:
        """
        Ensure tenant-specific schema exists for SEPARATE_SCHEMA mode.
        """
        if self.isolation_mode != TenantIsolationMode.SEPARATE_SCHEMA:
            return
        
        if tenant_id in self._initialized_tenant_schemas:
            return

        schema_name = self._get_schema_name(tenant_id)
        schema_sql = TENANT_SCHEMA_SQL.format(schema_name=schema_name)
        
        await conn.execute(schema_sql)
        self._initialized_tenant_schemas.add(tenant_id)
        logger.info(f"Created tenant schema: {schema_name}")

    async def _set_tenant_context(self, conn: asyncpg.Connection, tenant_id: str) -> None:
        """
        Set tenant context for RLS or search_path based on isolation mode.
        
        For SHARED_SCHEMA with RLS: SET LOCAL app.current_tenant = 'tenant_id'
        For SEPARATE_SCHEMA: SET search_path = tenant_xxx, public
        """
        if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA:
            schema_name = self._get_schema_name(tenant_id if tenant_id else None)
            await conn.execute(f"SET search_path = {schema_name}, public")
            logger.debug(f"Set search_path to {schema_name}")
        elif self.enable_rls:
            # Set app.current_tenant for RLS policies (empty string for global)
            # Use SET LOCAL to scope to current transaction in connection pool
            await conn.execute(f"SET LOCAL app.current_tenant_id = '{tenant_id}'")
            logger.debug(f"Set LOCAL app.current_tenant_id = '{tenant_id}'")
            # Verify it was set
            check = await conn.fetchval("SELECT current_setting('app.current_tenant_id', true)")
            logger.debug(f"Verified app.current_tenant_id = '{check}'")

    def _build_tenant_filter(self, tenant_id: str, table_alias: str = "") -> Tuple[str, List]:
        """
        Build SQL WHERE clause for tenant filtering in SHARED_SCHEMA mode without RLS.
        
        Returns:
            Tuple of (WHERE clause fragment, parameters list)
        """
        prefix = f"{table_alias}." if table_alias else ""
        # tenant_id is always a string, empty string for global namespace
        return f"{prefix}tenant_id = ${{param}}", [tenant_id]

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

    async def add_entity(self, entity: Entity, context: Optional[TenantContext] = None) -> None:
        """
        Add entity to PostgreSQL database
        
        Args:
            entity: Entity to add
            context: Optional tenant context for multi-tenant isolation
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        tenant_id = self._get_tenant_id(context)
        logger.debug(f"add_entity called with entity_id='{entity.id}', tenant_id='{tenant_id}', enable_rls={self.enable_rls}")
        
        # Set tenant_id on entity if context provided
        if tenant_id is not None and entity.tenant_id is None:
            entity.tenant_id = tenant_id

        # Serialize data
        properties_json = json.dumps(entity.properties)
        embedding_blob = self._serialize_embedding(entity.embedding) if entity.embedding else None

        async def _execute(conn: asyncpg.Connection):
            # Set tenant context (search_path or RLS)
            if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA and tenant_id:
                await self._ensure_tenant_schema(conn, tenant_id)
            
            if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA:
                # SEPARATE_SCHEMA: No tenant_id column
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
                # SHARED_SCHEMA: Include tenant_id column
                await conn.execute(
                    """
                    INSERT INTO graph_entities (id, tenant_id, entity_type, properties, embedding)
                    VALUES ($1, $2, $3, $4::jsonb, $5)
                    ON CONFLICT (id, tenant_id) DO UPDATE SET
                        entity_type = EXCLUDED.entity_type,
                        properties = EXCLUDED.properties,
                        embedding = EXCLUDED.embedding,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    entity.id,
                    tenant_id,
                    entity.entity_type,
                    properties_json,
                    embedding_blob,
                )

        if self._transaction_conn:
            await self._set_tenant_context(self._transaction_conn, tenant_id)
            await _execute(self._transaction_conn)
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                # Wrap in transaction if RLS is enabled (SET LOCAL requires transaction)
                if self.enable_rls:
                    async with conn.transaction():
                        await self._set_tenant_context(conn, tenant_id)
                        await _execute(conn)
                else:
                    await self._set_tenant_context(conn, tenant_id)
                    await _execute(conn)

    async def get_entity(self, entity_id: str, context: Optional[TenantContext] = None) -> Optional[Entity]:
        """
        Get entity from PostgreSQL database
        
        Args:
            entity_id: Entity ID to retrieve
            context: Optional tenant context for multi-tenant isolation
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        tenant_id = self._get_tenant_id(context)

        async def _fetch(conn: asyncpg.Connection):
            if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA:
                return await conn.fetchrow(
                    """
                    SELECT id, entity_type, properties, embedding
                    FROM graph_entities
                    WHERE id = $1
                    """,
                    entity_id,
                )
            elif self.enable_rls:
                # RLS will filter automatically
                return await conn.fetchrow(
                    """
                    SELECT id, tenant_id, entity_type, properties, embedding
                    FROM graph_entities
                    WHERE id = $1
                    """,
                    entity_id,
                )
            else:
                # Manual tenant filtering (tenant_id is always a string, '' for global)
                return await conn.fetchrow(
                    """
                    SELECT id, tenant_id, entity_type, properties, embedding
                    FROM graph_entities
                    WHERE id = $1 AND tenant_id = $2
                    """,
                    entity_id,
                    tenant_id,
                )

        if self._transaction_conn:
            await self._set_tenant_context(self._transaction_conn, tenant_id)
            row = await _fetch(self._transaction_conn)
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                # Wrap in transaction if RLS is enabled (SET LOCAL requires transaction)
                if self.enable_rls:
                    async with conn.transaction():
                        await self._set_tenant_context(conn, tenant_id)
                        row = await _fetch(conn)
                else:
                    await self._set_tenant_context(conn, tenant_id)
                    row = await _fetch(conn)

        if not row:
            return None

        # Deserialize
        properties = json.loads(row["properties"]) if isinstance(row["properties"], str) else row["properties"]
        embedding_raw = self._deserialize_embedding(row["embedding"]) if row["embedding"] else None
        embedding: Optional[List[float]] = cast(List[float], embedding_raw.tolist()) if embedding_raw is not None else None
        
        # Get tenant_id from row or context
        row_tenant_id = row.get("tenant_id") if "tenant_id" in row.keys() else tenant_id

        return Entity(
            id=row["id"],
            entity_type=row["entity_type"],
            properties=properties,
            embedding=embedding,
            tenant_id=row_tenant_id,
        )

    async def update_entity(self, entity: Entity, context: Optional[TenantContext] = None) -> None:
        """
        Update entity in PostgreSQL database
        
        Args:
            entity: Entity to update
            context: Optional tenant context for multi-tenant isolation
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        tenant_id = self._get_tenant_id(context)
        properties_json = json.dumps(entity.properties)
        embedding_blob = self._serialize_embedding(entity.embedding) if entity.embedding else None

        async def _execute(conn: asyncpg.Connection):
            if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA:
                return await conn.execute(
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
            elif self.enable_rls:
                return await conn.execute(
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
                # Manual tenant filtering (tenant_id is always a string, '' for global)
                return await conn.execute(
                    """
                    UPDATE graph_entities
                    SET entity_type = $2, properties = $3::jsonb, embedding = $4, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $1 AND tenant_id = $5
                    """,
                    entity.id,
                    entity.entity_type,
                    properties_json,
                    embedding_blob,
                    tenant_id,
                )

        if self._transaction_conn:
            await self._set_tenant_context(self._transaction_conn, tenant_id)
            result = await _execute(self._transaction_conn)
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                # Wrap in transaction if RLS is enabled (SET LOCAL requires transaction)
                if self.enable_rls:
                    async with conn.transaction():
                        await self._set_tenant_context(conn, tenant_id)
                        result = await _execute(conn)
                else:
                    await self._set_tenant_context(conn, tenant_id)
                    result = await _execute(conn)

        if result == "UPDATE 0":
            raise ValueError(f"Entity with ID '{entity.id}' not found")

    async def delete_entity(self, entity_id: str, context: Optional[TenantContext] = None) -> None:
        """
        Delete entity from PostgreSQL database
        
        Args:
            entity_id: Entity ID to delete
            context: Optional tenant context for multi-tenant isolation
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        tenant_id = self._get_tenant_id(context)

        async def _execute(conn: asyncpg.Connection):
            if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA or self.enable_rls:
                # Delete relations first
                await conn.execute(
                    "DELETE FROM graph_relations WHERE source_id = $1 OR target_id = $1",
                    entity_id
                )
                return await conn.execute("DELETE FROM graph_entities WHERE id = $1", entity_id)
            else:
                # Manual tenant filtering (tenant_id is always a string, '' for global)
                await conn.execute(
                    "DELETE FROM graph_relations WHERE (source_id = $1 OR target_id = $1) AND tenant_id = $2",
                    entity_id,
                    tenant_id
                )
                return await conn.execute(
                    "DELETE FROM graph_entities WHERE id = $1 AND tenant_id = $2",
                    entity_id,
                    tenant_id
                )

        if self._transaction_conn:
            await self._set_tenant_context(self._transaction_conn, tenant_id)
            result = await _execute(self._transaction_conn)
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                # Wrap in transaction if RLS is enabled (SET LOCAL requires transaction)
                if self.enable_rls:
                    async with conn.transaction():
                        await self._set_tenant_context(conn, tenant_id)
                        result = await _execute(conn)
                else:
                    await self._set_tenant_context(conn, tenant_id)
                    result = await _execute(conn)

        if result == "DELETE 0":
            raise ValueError(f"Entity with ID '{entity_id}' not found")

    async def add_relation(self, relation: Relation, context: Optional[TenantContext] = None) -> None:
        """
        Add relation to PostgreSQL database
        
        Args:
            relation: Relation to add
            context: Optional tenant context for multi-tenant isolation
            
        Raises:
            CrossTenantRelationError: If source and target entities belong to different tenants
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        tenant_id = self._get_tenant_id(context)
        
        # Check entities exist and enforce same-tenant constraint
        source_entity = await self.get_entity(relation.source_id, context=context)
        target_entity = await self.get_entity(relation.target_id, context=context)
        
        if not source_entity:
            raise ValueError(f"Source entity '{relation.source_id}' does not exist")
        if not target_entity:
            raise ValueError(f"Target entity '{relation.target_id}' does not exist")

        # Enforce same-tenant constraint (skip for global namespace which has empty tenant_id)
        if tenant_id:
            if source_entity.tenant_id != target_entity.tenant_id:
                raise CrossTenantRelationError(source_entity.tenant_id, target_entity.tenant_id)

        # Set tenant_id on relation
        if relation.tenant_id is None:
            relation.tenant_id = tenant_id

        properties_json = json.dumps(relation.properties)

        async def _execute(conn: asyncpg.Connection):
            if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA and tenant_id:
                await self._ensure_tenant_schema(conn, tenant_id)
            
            if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA:
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
                await conn.execute(
                    """
                    INSERT INTO graph_relations (id, tenant_id, relation_type, source_id, target_id, properties, weight)
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)
                    ON CONFLICT (id, tenant_id) DO UPDATE SET
                        relation_type = EXCLUDED.relation_type,
                        source_id = EXCLUDED.source_id,
                        target_id = EXCLUDED.target_id,
                        properties = EXCLUDED.properties,
                        weight = EXCLUDED.weight,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    relation.id,
                    tenant_id,
                    relation.relation_type,
                    relation.source_id,
                    relation.target_id,
                    properties_json,
                    relation.weight,
                )

        if self._transaction_conn:
            await self._set_tenant_context(self._transaction_conn, tenant_id)
            await _execute(self._transaction_conn)
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                # Wrap in transaction if RLS is enabled (SET LOCAL requires transaction)
                if self.enable_rls:
                    async with conn.transaction():
                        await self._set_tenant_context(conn, tenant_id)
                        await _execute(conn)
                else:
                    await self._set_tenant_context(conn, tenant_id)
                    await _execute(conn)

    async def get_relation(self, relation_id: str, context: Optional[TenantContext] = None) -> Optional[Relation]:
        """
        Get relation from PostgreSQL database
        
        Args:
            relation_id: Relation ID to retrieve
            context: Optional tenant context for multi-tenant isolation
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        tenant_id = self._get_tenant_id(context)

        async def _fetch(conn: asyncpg.Connection):
            if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA:
                return await conn.fetchrow(
                    """
                    SELECT id, relation_type, source_id, target_id, properties, weight
                    FROM graph_relations
                    WHERE id = $1
                    """,
                    relation_id,
                )
            elif self.enable_rls:
                return await conn.fetchrow(
                    """
                    SELECT id, tenant_id, relation_type, source_id, target_id, properties, weight
                    FROM graph_relations
                    WHERE id = $1
                    """,
                    relation_id,
                )
            else:
                # Manual tenant filtering (tenant_id is always a string, '' for global)
                return await conn.fetchrow(
                    """
                    SELECT id, tenant_id, relation_type, source_id, target_id, properties, weight
                    FROM graph_relations
                    WHERE id = $1 AND tenant_id = $2
                    """,
                    relation_id,
                    tenant_id,
                )

        if self._transaction_conn:
            await self._set_tenant_context(self._transaction_conn, tenant_id)
            row = await _fetch(self._transaction_conn)
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                # Wrap in transaction if RLS is enabled (SET LOCAL requires transaction)
                if self.enable_rls:
                    async with conn.transaction():
                        await self._set_tenant_context(conn, tenant_id)
                        row = await _fetch(conn)
                else:
                    await self._set_tenant_context(conn, tenant_id)
                    row = await _fetch(conn)

        if not row:
            return None

        properties = json.loads(row["properties"]) if isinstance(row["properties"], str) else row["properties"]
        row_tenant_id = row.get("tenant_id") if "tenant_id" in row.keys() else tenant_id

        return Relation(
            id=row["id"],
            relation_type=row["relation_type"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            properties=properties,
            weight=float(row["weight"]) if row["weight"] else 1.0,
            tenant_id=row_tenant_id,
        )

    async def delete_relation(self, relation_id: str, context: Optional[TenantContext] = None) -> None:
        """
        Delete relation from PostgreSQL database
        
        Args:
            relation_id: Relation ID to delete
            context: Optional tenant context for multi-tenant isolation
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        tenant_id = self._get_tenant_id(context)

        async def _execute(conn: asyncpg.Connection):
            if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA or self.enable_rls:
                return await conn.execute("DELETE FROM graph_relations WHERE id = $1", relation_id)
            else:
                # Manual tenant filtering (tenant_id is always a string, '' for global)
                return await conn.execute(
                    "DELETE FROM graph_relations WHERE id = $1 AND tenant_id = $2",
                    relation_id,
                    tenant_id
                )

        if self._transaction_conn:
            await self._set_tenant_context(self._transaction_conn, tenant_id)
            result = await _execute(self._transaction_conn)
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                # Wrap in transaction if RLS is enabled (SET LOCAL requires transaction)
                if self.enable_rls:
                    async with conn.transaction():
                        await self._set_tenant_context(conn, tenant_id)
                        result = await _execute(conn)
                else:
                    await self._set_tenant_context(conn, tenant_id)
                    result = await _execute(conn)

        if result == "DELETE 0":
            raise ValueError(f"Relation with ID '{relation_id}' not found")

    async def get_neighbors(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        direction: str = "outgoing",
        context: Optional[TenantContext] = None,
    ) -> List[Entity]:
        """
        Get neighboring entities (optimized with SQL)
        
        Args:
            entity_id: ID of entity to get neighbors for
            relation_type: Optional filter by relation type
            direction: "outgoing", "incoming", or "both"
            context: Optional tenant context for multi-tenant isolation
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        tenant_id = self._get_tenant_id(context)

        async def _fetch(conn: asyncpg.Connection):
            # For SEPARATE_SCHEMA or RLS, the context handles filtering
            use_tenant_filter = not (self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA or self.enable_rls)
            
            # Build query based on direction
            if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA:
                # No tenant_id column in SEPARATE_SCHEMA
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
                params: List[Any] = [entity_id]
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
            else:
                # SHARED_SCHEMA with tenant_id column (tenant_id is always a string, '' for global)
                tenant_filter = ""
                if use_tenant_filter:
                    tenant_filter = "AND e.tenant_id = $2 AND r.tenant_id = $2"
                
                if direction == "outgoing":
                    query = f"""
                        SELECT DISTINCT e.id, e.tenant_id, e.entity_type, e.properties, e.embedding
                        FROM graph_entities e
                        JOIN graph_relations r ON e.id = r.target_id
                        WHERE r.source_id = $1 {tenant_filter}
                    """
                elif direction == "incoming":
                    query = f"""
                        SELECT DISTINCT e.id, e.tenant_id, e.entity_type, e.properties, e.embedding
                        FROM graph_entities e
                        JOIN graph_relations r ON e.id = r.source_id
                        WHERE r.target_id = $1 {tenant_filter}
                    """
                else:  # both
                    inner_filter = "AND tenant_id = $2" if use_tenant_filter else ""
                    query = f"""
                        SELECT DISTINCT e.id, e.tenant_id, e.entity_type, e.properties, e.embedding
                        FROM graph_entities e
                        WHERE e.id IN (
                            SELECT target_id FROM graph_relations WHERE source_id = $1 {inner_filter}
                            UNION
                            SELECT source_id FROM graph_relations WHERE target_id = $1 {inner_filter}
                        )
                    """
                    if use_tenant_filter:
                        query += " AND e.tenant_id = $2"
                
                params = [entity_id]
                if use_tenant_filter:
                    params.append(tenant_id)
                
                if relation_type:
                    param_idx = len(params) + 1
                    if direction == "both":
                        query = query.replace(
                            "SELECT target_id FROM graph_relations WHERE source_id = $1",
                            f"SELECT target_id FROM graph_relations WHERE source_id = $1 AND relation_type = ${param_idx}",
                        )
                        query = query.replace(
                            "SELECT source_id FROM graph_relations WHERE target_id = $1",
                            f"SELECT source_id FROM graph_relations WHERE target_id = $1 AND relation_type = ${param_idx}",
                        )
                    else:
                        query += f" AND r.relation_type = ${param_idx}"
                    params.append(relation_type)
            
            return await conn.fetch(query, *params)

        if self._transaction_conn:
            await self._set_tenant_context(self._transaction_conn, tenant_id)
            rows = await _fetch(self._transaction_conn)
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                # Wrap in transaction if RLS is enabled (SET LOCAL requires transaction)
                if self.enable_rls:
                    async with conn.transaction():
                        await self._set_tenant_context(conn, tenant_id)
                        rows = await _fetch(conn)
                else:
                    await self._set_tenant_context(conn, tenant_id)
                    rows = await _fetch(conn)

        entities = []
        for row in rows:
            properties = json.loads(row["properties"]) if isinstance(row["properties"], str) else row["properties"]
            embedding_raw = self._deserialize_embedding(row["embedding"]) if row["embedding"] else None
            embedding: Optional[List[float]] = cast(List[float], embedding_raw.tolist()) if embedding_raw is not None else None
            row_tenant_id = row.get("tenant_id") if "tenant_id" in row.keys() else tenant_id
            entities.append(
                Entity(
                    id=row["id"],
                    entity_type=row["entity_type"],
                    properties=properties,
                    embedding=embedding,
                    tenant_id=row_tenant_id,
                )
            )

        return entities

    async def get_all_entities(
        self,
        entity_type: Optional[str] = None,
        limit: Optional[int] = None,
        context: Optional[TenantContext] = None,
    ) -> List[Entity]:
        """
        Get all entities, optionally filtered by type
        
        Args:
            entity_type: Optional filter by entity type
            limit: Optional limit on number of entities
            context: Optional tenant context for multi-tenant isolation
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        tenant_id = self._get_tenant_id(context)
        logger.debug(f"get_all_entities called with tenant_id='{tenant_id}', enable_rls={self.enable_rls}, isolation_mode={self.isolation_mode}")

        async def _fetch(conn: asyncpg.Connection):
            if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA:
                query = "SELECT id, entity_type, properties, embedding FROM graph_entities"
                params: List[Any] = []
                
                if entity_type:
                    query += " WHERE entity_type = $1"
                    params.append(entity_type)
                
                if limit:
                    query += f" LIMIT ${len(params) + 1}"
                    params.append(limit)
            elif self.enable_rls:
                query = "SELECT id, tenant_id, entity_type, properties, embedding FROM graph_entities"
                params = []
                
                if entity_type:
                    query += " WHERE entity_type = $1"
                    params.append(entity_type)
                
                if limit:
                    query += f" LIMIT ${len(params) + 1}"
                    params.append(limit)
            else:
                # Manual tenant filtering (tenant_id is always a string, '' for global)
                query = "SELECT id, tenant_id, entity_type, properties, embedding FROM graph_entities WHERE tenant_id = $1"
                params = [tenant_id]
                
                if entity_type:
                    query += f" AND entity_type = ${len(params) + 1}"
                    params.append(entity_type)
                
                if limit:
                    query += f" LIMIT ${len(params) + 1}"
                    params.append(limit)
            
            return await conn.fetch(query, *params)

        if self._transaction_conn:
            await self._set_tenant_context(self._transaction_conn, tenant_id)
            rows = await _fetch(self._transaction_conn)
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                # Wrap in transaction if RLS is enabled (SET LOCAL requires transaction)
                if self.enable_rls:
                    async with conn.transaction():
                        await self._set_tenant_context(conn, tenant_id)
                        rows = await _fetch(conn)
                else:
                    await self._set_tenant_context(conn, tenant_id)
                    rows = await _fetch(conn)

        logger.debug(f"get_all_entities query returned {len(rows)} rows")
        entities = []
        for row in rows:
            properties = json.loads(row["properties"]) if isinstance(row["properties"], str) else row["properties"]
            embedding_raw = self._deserialize_embedding(row["embedding"]) if row["embedding"] else None
            embedding: Optional[List[float]] = cast(List[float], embedding_raw.tolist()) if embedding_raw is not None else None
            row_tenant_id = row.get("tenant_id") if "tenant_id" in row.keys() else tenant_id
            logger.debug(f"Retrieved entity id='{row['id']}', tenant_id='{row_tenant_id}'")
            entities.append(
                Entity(
                    id=row["id"],
                    entity_type=row["entity_type"],
                    properties=properties,
                    embedding=embedding,
                    tenant_id=row_tenant_id,
                )
            )

        logger.debug(f"get_all_entities returning {len(entities)} entities for requested tenant_id='{tenant_id}'")
        return entities

    async def get_stats(self, context: Optional[TenantContext] = None) -> Dict[str, Any]:
        """
        Get graph statistics
        
        Args:
            context: Optional tenant context for tenant-scoped stats
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        tenant_id = self._get_tenant_id(context)

        async def _fetch(conn: asyncpg.Connection):
            if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA or self.enable_rls:
                entity_count = await conn.fetchval("SELECT COUNT(*) FROM graph_entities")
                relation_count = await conn.fetchval("SELECT COUNT(*) FROM graph_relations")
                entity_types = await conn.fetch("SELECT entity_type, COUNT(*) as count FROM graph_entities GROUP BY entity_type")
                relation_types = await conn.fetch("SELECT relation_type, COUNT(*) as count FROM graph_relations GROUP BY relation_type")
            else:
                # Manual tenant filtering (tenant_id is always a string, '' for global)
                entity_count = await conn.fetchval("SELECT COUNT(*) FROM graph_entities WHERE tenant_id = $1", tenant_id)
                relation_count = await conn.fetchval("SELECT COUNT(*) FROM graph_relations WHERE tenant_id = $1", tenant_id)
                entity_types = await conn.fetch("SELECT entity_type, COUNT(*) as count FROM graph_entities WHERE tenant_id = $1 GROUP BY entity_type", tenant_id)
                relation_types = await conn.fetch("SELECT relation_type, COUNT(*) as count FROM graph_relations WHERE tenant_id = $1 GROUP BY relation_type", tenant_id)
            
            return entity_count, relation_count, entity_types, relation_types

        if self._transaction_conn:
            await self._set_tenant_context(self._transaction_conn, tenant_id)
            entity_count, relation_count, entity_types, relation_types = await _fetch(self._transaction_conn)
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                # Wrap in transaction if RLS is enabled (SET LOCAL requires transaction)
                if self.enable_rls:
                    async with conn.transaction():
                        await self._set_tenant_context(conn, tenant_id)
                        entity_count, relation_count, entity_types, relation_types = await _fetch(conn)
                else:
                    await self._set_tenant_context(conn, tenant_id)
                    entity_count, relation_count, entity_types, relation_types = await _fetch(conn)

        return {
            "entity_count": entity_count,
            "relation_count": relation_count,
            "entity_types": {row["entity_type"]: row["count"] for row in entity_types},
            "relation_types": {row["relation_type"]: row["count"] for row in relation_types},
            "backend": "postgresql",
            "pool_size": (f"{self.pool.get_size()}/{self.max_pool_size}" if self.pool else "0/0"),
            "isolation_mode": self.isolation_mode.value,
            "tenant_id": tenant_id,
            "enable_rls": self.enable_rls,
        }

    async def clear(self, context: Optional[TenantContext] = None) -> None:
        """
        Clear data from PostgreSQL database
        
        Args:
            context: Optional tenant context for multi-tenant isolation.
                    If provided, clears only data for the specified tenant.
                    If None (no context), clears ALL data across all tenants.
        """
        if not self._is_initialized:
            raise RuntimeError("GraphStore not initialized")

        # Note: context=None means clear ALL data, not just global namespace
        clear_all = context is None
        tenant_id = self._get_tenant_id(context)

        async def _execute(conn: asyncpg.Connection):
            if clear_all:
                # Clear all data across all tenants
                await conn.execute("DELETE FROM graph_relations")
                await conn.execute("DELETE FROM graph_entities")
                
                # Drop tenant schemas for SEPARATE_SCHEMA mode
                if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA:
                    schemas = await conn.fetch(
                        "SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%'"
                    )
                    for row in schemas:
                        await conn.execute(f"DROP SCHEMA IF EXISTS {row['schema_name']} CASCADE")
                    self._initialized_tenant_schemas.clear()
            else:
                if self.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA:
                    # Drop tenant schema
                    schema_name = self._get_schema_name(tenant_id if tenant_id else None)
                    await conn.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
                    self._initialized_tenant_schemas.discard(tenant_id)
                elif self.enable_rls:
                    # RLS will filter automatically
                    await conn.execute("DELETE FROM graph_relations")
                    await conn.execute("DELETE FROM graph_entities")
                else:
                    # Manual tenant filtering (tenant_id is string, '' for global)
                    await conn.execute("DELETE FROM graph_relations WHERE tenant_id = $1", tenant_id)
                    await conn.execute("DELETE FROM graph_entities WHERE tenant_id = $1", tenant_id)

        if self._transaction_conn:
            await self._set_tenant_context(self._transaction_conn, tenant_id)
            await _execute(self._transaction_conn)
        else:
            pool = self._ensure_pool()
            async with pool.acquire() as conn:
                # Wrap in transaction if RLS is enabled (SET LOCAL requires transaction)
                if self.enable_rls and not clear_all:
                    async with conn.transaction():
                        await self._set_tenant_context(conn, tenant_id)
                        await _execute(conn)
                else:
                    if not clear_all:
                        await self._set_tenant_context(conn, tenant_id)
                    await _execute(conn)

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
