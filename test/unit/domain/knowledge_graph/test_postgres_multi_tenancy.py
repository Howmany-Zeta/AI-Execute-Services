"""
Unit tests for PostgresGraphStore multi-tenancy support.

Note: These tests require a PostgreSQL database. They will be skipped if 
the database is not available. Configuration is loaded from .env.PostgreSQL file.

Tests:
- SHARED_SCHEMA mode with tenant_id column filtering
- SHARED_SCHEMA mode with RLS
- SEPARATE_SCHEMA mode with PostgreSQL schemas
- Cross-tenant isolation
- Same-tenant constraint for relations
"""

import os
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.infrastructure.graph_storage.postgres import (
    PostgresGraphStore,
    SCHEMA_SQL,
    RLS_SETUP_SQL,
    TENANT_SCHEMA_SQL,
)
from aiecs.infrastructure.graph_storage.tenant import (
    TenantContext,
    TenantIsolationMode,
    CrossTenantRelationError,
)


def load_postgres_config():
    """Load PostgreSQL configuration from .env.PostgreSQL file."""
    env_file = Path(__file__).parents[3] / ".env.PostgreSQL"
    
    if not env_file.exists():
        return None
    
    config = {}
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    
    return config


# Load PostgreSQL configuration
PG_CONFIG = load_postgres_config()

# Check if PostgreSQL is available for integration tests
if PG_CONFIG:
    if PG_CONFIG.get("DB_CONNECTION_MODE") == "cloud":
        POSTGRES_TEST_DSN = PG_CONFIG.get("POSTGRES_URL")
    else:
        # Build DSN from individual parameters
        host = PG_CONFIG.get("DB_HOST", "localhost")
        port = PG_CONFIG.get("DB_PORT", "5432")
        user = PG_CONFIG.get("DB_USER", "postgres")
        password = PG_CONFIG.get("DB_PASSWORD", "")
        database = PG_CONFIG.get("DB_NAME", "aiecs_knowledge_graph")
        POSTGRES_TEST_DSN = f"postgresql://{user}:{password}@{host}:{port}/{database}"
else:
    POSTGRES_TEST_DSN = os.environ.get("POSTGRES_TEST_DSN")

SKIP_POSTGRES_TESTS = POSTGRES_TEST_DSN is None


# =============================================================================
# Unit Tests (no database required)
# =============================================================================

class TestPostgresMultiTenancyConfig:
    """Test configuration options."""

    def test_default_isolation_mode(self):
        """Test default isolation mode is SHARED_SCHEMA."""
        with patch('aiecs.infrastructure.graph_storage.postgres.get_settings') as mock_settings:
            mock_settings.return_value.database_config = {"host": "localhost", "port": 5432}
            store = PostgresGraphStore()
            assert store.isolation_mode == TenantIsolationMode.SHARED_SCHEMA
            assert store.enable_rls is False

    def test_custom_isolation_mode(self):
        """Test custom isolation mode configuration."""
        with patch('aiecs.infrastructure.graph_storage.postgres.get_settings') as mock_settings:
            mock_settings.return_value.database_config = {"host": "localhost", "port": 5432}
            store = PostgresGraphStore(
                isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA,
                enable_rls=True
            )
            assert store.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA
            assert store.enable_rls is True

    def test_get_tenant_id_with_context(self):
        """Test _get_tenant_id with context."""
        with patch('aiecs.infrastructure.graph_storage.postgres.get_settings') as mock_settings:
            mock_settings.return_value.database_config = {"host": "localhost", "port": 5432}
            store = PostgresGraphStore()
            context = TenantContext(tenant_id="test-tenant")
            assert store._get_tenant_id(context) == "test-tenant"

    def test_get_tenant_id_without_context(self):
        """Test _get_tenant_id without context returns empty string for global namespace."""
        with patch('aiecs.infrastructure.graph_storage.postgres.get_settings') as mock_settings:
            mock_settings.return_value.database_config = {"host": "localhost", "port": 5432}
            store = PostgresGraphStore()
            # Empty string represents global namespace (not None)
            assert store._get_tenant_id(None) == ""

    def test_get_schema_name_global(self):
        """Test _get_schema_name for global namespace."""
        with patch('aiecs.infrastructure.graph_storage.postgres.get_settings') as mock_settings:
            mock_settings.return_value.database_config = {"host": "localhost", "port": 5432}
            store = PostgresGraphStore()
            assert store._get_schema_name(None) == "public"

    def test_get_schema_name_tenant(self):
        """Test _get_schema_name for tenant."""
        with patch('aiecs.infrastructure.graph_storage.postgres.get_settings') as mock_settings:
            mock_settings.return_value.database_config = {"host": "localhost", "port": 5432}
            store = PostgresGraphStore()
            assert store._get_schema_name("acme-corp") == "tenant_acme_corp"


class TestSchemaSQL:
    """Test SQL schema templates."""

    def test_schema_has_tenant_id_column(self):
        """Test that schema SQL includes tenant_id columns."""
        assert "tenant_id TEXT" in SCHEMA_SQL
        assert "PRIMARY KEY (id, tenant_id)" in SCHEMA_SQL
        # tenant_id uses empty string as default for global namespace
        assert "DEFAULT ''" in SCHEMA_SQL

    def test_schema_has_tenant_indexes(self):
        """Test that schema SQL includes tenant indexes."""
        assert "idx_graph_entities_tenant" in SCHEMA_SQL
        assert "idx_graph_relations_tenant" in SCHEMA_SQL

    def test_rls_setup_sql(self):
        """Test RLS setup SQL contains required policies."""
        assert "ENABLE ROW LEVEL SECURITY" in RLS_SETUP_SQL
        assert "tenant_isolation_entities" in RLS_SETUP_SQL
        assert "tenant_isolation_relations" in RLS_SETUP_SQL
        assert "app.current_tenant" in RLS_SETUP_SQL

    def test_tenant_schema_sql_template(self):
        """Test tenant schema SQL template."""
        assert "{schema_name}" in TENANT_SCHEMA_SQL
        schema_sql = TENANT_SCHEMA_SQL.format(schema_name="tenant_test")
        assert "CREATE SCHEMA IF NOT EXISTS tenant_test" in schema_sql
        assert "tenant_test.graph_entities" in schema_sql
        # Verify escaped braces are resolved to actual JSON syntax
        assert "{}" in schema_sql  # JSONB default value


# =============================================================================
# Integration Tests (requires PostgreSQL)
# =============================================================================

@pytest.fixture
async def pg_store_shared():
    """Create PostgresGraphStore with SHARED_SCHEMA mode."""
    if SKIP_POSTGRES_TESTS:
        pytest.skip("PostgreSQL not available")
    
    store = PostgresGraphStore(
        dsn=POSTGRES_TEST_DSN,
        isolation_mode=TenantIsolationMode.SHARED_SCHEMA,
        enable_rls=False,
    )
    await store.initialize()
    yield store
    # Clean up
    await store.clear()
    await store.close()


@pytest.fixture
async def pg_store_rls():
    """Create PostgresGraphStore with RLS enabled."""
    if SKIP_POSTGRES_TESTS:
        pytest.skip("PostgreSQL not available")
    
    store = PostgresGraphStore(
        dsn=POSTGRES_TEST_DSN,
        isolation_mode=TenantIsolationMode.SHARED_SCHEMA,
        enable_rls=True,
    )
    await store.initialize()
    yield store
    # Clean up
    await store.clear()
    await store.close()


@pytest.fixture
async def pg_store_separate():
    """Create PostgresGraphStore with SEPARATE_SCHEMA mode."""
    if SKIP_POSTGRES_TESTS:
        pytest.skip("PostgreSQL not available")
    
    store = PostgresGraphStore(
        dsn=POSTGRES_TEST_DSN,
        isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA,
    )
    await store.initialize()
    yield store
    # Clean up
    await store.clear()
    await store.close()


@pytest.mark.skipif(SKIP_POSTGRES_TESTS, reason="PostgreSQL not available")
class TestSharedSchemaMode:
    """Integration tests for SHARED_SCHEMA mode."""

    @pytest.mark.asyncio
    async def test_add_entity_with_tenant(self, pg_store_shared):
        """Test adding entity with tenant context."""
        context = TenantContext(tenant_id="tenant-a")
        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await pg_store_shared.add_entity(entity, context=context)

        result = await pg_store_shared.get_entity("e1", context=context)
        assert result is not None
        assert result.tenant_id == "tenant-a"

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, pg_store_shared):
        """Test tenant isolation."""
        context_a = TenantContext(tenant_id="tenant-a")
        context_b = TenantContext(tenant_id="tenant-b")

        # Add entity to tenant A
        await pg_store_shared.add_entity(
            Entity(id="e1", entity_type="Person", properties={"name": "Alice"}),
            context=context_a
        )

        # Add entity with same ID to tenant B
        await pg_store_shared.add_entity(
            Entity(id="e1", entity_type="Person", properties={"name": "Bob"}),
            context=context_b
        )

        # Verify isolation
        result_a = await pg_store_shared.get_entity("e1", context=context_a)
        result_b = await pg_store_shared.get_entity("e1", context=context_b)

        assert result_a.properties["name"] == "Alice"
        assert result_b.properties["name"] == "Bob"

    @pytest.mark.asyncio
    async def test_relation_same_tenant_constraint(self, pg_store_shared):
        """Test that relations require same tenant."""
        context = TenantContext(tenant_id="tenant-a")

        # Add entities
        await pg_store_shared.add_entity(
            Entity(id="e1", entity_type="Person", properties={}),
            context=context
        )
        await pg_store_shared.add_entity(
            Entity(id="e2", entity_type="Person", properties={}),
            context=context
        )

        # Add relation - should succeed
        relation = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        await pg_store_shared.add_relation(relation, context=context)

        result = await pg_store_shared.get_relation("r1", context=context)
        assert result is not None


@pytest.mark.skipif(SKIP_POSTGRES_TESTS, reason="PostgreSQL not available")
class TestRLSMode:
    """Integration tests for RLS mode."""

    @pytest.mark.asyncio
    async def test_rls_filtering(self, pg_store_rls):
        """Test that RLS filters entities automatically."""
        context_a = TenantContext(tenant_id="tenant-a")
        context_b = TenantContext(tenant_id="tenant-b")

        # Add entities to different tenants
        await pg_store_rls.add_entity(
            Entity(id="ea", entity_type="Person", properties={"name": "Alice"}),
            context=context_a
        )
        await pg_store_rls.add_entity(
            Entity(id="eb", entity_type="Person", properties={"name": "Bob"}),
            context=context_b
        )

        # Get all entities for tenant A - should only see tenant A's entities
        entities = await pg_store_rls.get_all_entities(context=context_a)
        assert len(entities) == 1
        assert entities[0].id == "ea"


@pytest.mark.skipif(SKIP_POSTGRES_TESTS, reason="PostgreSQL not available")
class TestSeparateSchemaMode:
    """Integration tests for SEPARATE_SCHEMA mode."""

    @pytest.mark.asyncio
    async def test_tenant_schema_creation(self, pg_store_separate):
        """Test that tenant schemas are created on demand."""
        context = TenantContext(tenant_id="new-tenant")
        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        
        await pg_store_separate.add_entity(entity, context=context)
        
        # Schema should be tracked
        assert "new-tenant" in pg_store_separate._initialized_tenant_schemas

    @pytest.mark.asyncio
    async def test_tenant_isolation_separate_schema(self, pg_store_separate):
        """Test tenant isolation with separate schemas."""
        context_a = TenantContext(tenant_id="schema-tenant-a")
        context_b = TenantContext(tenant_id="schema-tenant-b")

        # Add entity to each tenant
        await pg_store_separate.add_entity(
            Entity(id="e1", entity_type="Person", properties={"name": "Alice"}),
            context=context_a
        )
        await pg_store_separate.add_entity(
            Entity(id="e1", entity_type="Person", properties={"name": "Bob"}),
            context=context_b
        )

        # Verify isolation
        result_a = await pg_store_separate.get_entity("e1", context=context_a)
        result_b = await pg_store_separate.get_entity("e1", context=context_b)

        assert result_a.properties["name"] == "Alice"
        assert result_b.properties["name"] == "Bob"


@pytest.mark.skipif(SKIP_POSTGRES_TESTS, reason="PostgreSQL not available")
class TestClearOperations:
    """Integration tests for clear operations."""

    @pytest.mark.asyncio
    async def test_clear_tenant(self, pg_store_shared):
        """Test clearing a specific tenant."""
        context_a = TenantContext(tenant_id="tenant-a")
        context_b = TenantContext(tenant_id="tenant-b")

        # Add entities
        await pg_store_shared.add_entity(
            Entity(id="ea", entity_type="Person", properties={}),
            context=context_a
        )
        await pg_store_shared.add_entity(
            Entity(id="eb", entity_type="Person", properties={}),
            context=context_b
        )

        # Clear tenant A
        await pg_store_shared.clear(context=context_a)

        # Tenant A should be empty
        assert await pg_store_shared.get_entity("ea", context=context_a) is None

        # Tenant B should still have data
        assert await pg_store_shared.get_entity("eb", context=context_b) is not None
