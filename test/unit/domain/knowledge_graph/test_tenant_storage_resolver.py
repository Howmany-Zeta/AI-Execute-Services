"""
Unit tests for TenantAwareStorageResolver

Tests the storage path resolution logic for multi-tenant graph storage backends.
"""

import pytest
from aiecs.infrastructure.graph_storage.tenant import (
    TenantContext,
    TenantIsolationMode,
    TenantAwareStorageResolver,
    InvalidTenantIdError,
)


class TestTenantAwareStorageResolver:
    """Test suite for TenantAwareStorageResolver"""

    def test_init_default_prefixes(self):
        """Test resolver initialization with default prefixes"""
        resolver = TenantAwareStorageResolver()
        assert resolver.table_prefix == "tenant"
        assert resolver.schema_prefix == "tenant"

    def test_init_custom_prefixes(self):
        """Test resolver initialization with custom prefixes"""
        resolver = TenantAwareStorageResolver(
            table_prefix="custom_tenant",
            schema_prefix="schema_tenant"
        )
        assert resolver.table_prefix == "custom_tenant"
        assert resolver.schema_prefix == "schema_tenant"

    def test_resolve_table_name_no_context(self):
        """Test table name resolution without tenant context"""
        resolver = TenantAwareStorageResolver()
        table_name = resolver.resolve_table_name("entities", None)
        assert table_name == "entities"

    def test_resolve_table_name_disabled_mode(self):
        """Test table name resolution with DISABLED isolation mode"""
        resolver = TenantAwareStorageResolver()
        context = TenantContext(
            tenant_id="acme",
            isolation_mode=TenantIsolationMode.DISABLED
        )
        table_name = resolver.resolve_table_name("entities", context)
        assert table_name == "entities"

    def test_resolve_table_name_shared_schema_mode(self):
        """Test table name resolution with SHARED_SCHEMA mode"""
        resolver = TenantAwareStorageResolver()
        context = TenantContext(
            tenant_id="acme",
            isolation_mode=TenantIsolationMode.SHARED_SCHEMA
        )
        table_name = resolver.resolve_table_name("entities", context)
        # SHARED_SCHEMA uses base table with tenant_id column filtering
        assert table_name == "entities"

    def test_resolve_table_name_separate_schema_mode(self):
        """Test table name resolution with SEPARATE_SCHEMA mode"""
        resolver = TenantAwareStorageResolver()
        context = TenantContext(
            tenant_id="acme",
            isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
        )
        table_name = resolver.resolve_table_name("entities", context)
        # SEPARATE_SCHEMA uses prefixed table names
        assert table_name == "tenant_acme_entities"

    def test_resolve_table_name_separate_schema_custom_prefix(self):
        """Test table name resolution with custom prefix"""
        resolver = TenantAwareStorageResolver(table_prefix="org")
        context = TenantContext(
            tenant_id="acme-corp",
            isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
        )
        table_name = resolver.resolve_table_name("relations", context)
        assert table_name == "org_acme-corp_relations"

    def test_resolve_schema_name_no_context(self):
        """Test schema name resolution without context"""
        resolver = TenantAwareStorageResolver()
        schema_name = resolver.resolve_schema_name(None)
        assert schema_name is None

    def test_resolve_schema_name_disabled_mode(self):
        """Test schema name resolution with DISABLED mode"""
        resolver = TenantAwareStorageResolver()
        context = TenantContext(
            tenant_id="acme",
            isolation_mode=TenantIsolationMode.DISABLED
        )
        schema_name = resolver.resolve_schema_name(context)
        assert schema_name is None

    def test_resolve_schema_name_shared_schema_mode(self):
        """Test schema name resolution with SHARED_SCHEMA mode"""
        resolver = TenantAwareStorageResolver()
        context = TenantContext(
            tenant_id="acme",
            isolation_mode=TenantIsolationMode.SHARED_SCHEMA
        )
        schema_name = resolver.resolve_schema_name(context)
        # SHARED_SCHEMA doesn't use separate schemas
        assert schema_name is None

    def test_resolve_schema_name_separate_schema_mode(self):
        """Test schema name resolution with SEPARATE_SCHEMA mode"""
        resolver = TenantAwareStorageResolver()
        context = TenantContext(
            tenant_id="acme",
            isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
        )
        schema_name = resolver.resolve_schema_name(context)
        assert schema_name == "tenant_acme"

    def test_resolve_schema_name_custom_prefix(self):
        """Test schema name resolution with custom prefix"""
        resolver = TenantAwareStorageResolver(schema_prefix="org_schema")
        context = TenantContext(
            tenant_id="acme-corp",
            isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
        )
        schema_name = resolver.resolve_schema_name(context)
        assert schema_name == "org_schema_acme-corp"

    def test_resolve_database_path_no_context(self):
        """Test database path resolution without context"""
        resolver = TenantAwareStorageResolver()
        db_path = resolver.resolve_database_path("/data/graph.db", None)
        assert db_path == "/data/graph.db"

    def test_resolve_database_path_shared_schema_mode(self):
        """Test database path resolution with SHARED_SCHEMA mode"""
        resolver = TenantAwareStorageResolver()
        context = TenantContext(
            tenant_id="acme",
            isolation_mode=TenantIsolationMode.SHARED_SCHEMA
        )
        db_path = resolver.resolve_database_path("/data/graph.db", context)
        # SHARED_SCHEMA uses same database
        assert db_path == "/data/graph.db"

    def test_resolve_database_path_separate_schema_mode(self):
        """Test database path resolution with SEPARATE_SCHEMA mode"""
        resolver = TenantAwareStorageResolver()
        context = TenantContext(
            tenant_id="acme",
            isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
        )
        db_path = resolver.resolve_database_path("/data/graph.db", context)
        # SEPARATE_SCHEMA uses tenant-specific database file
        assert db_path == "/data/tenant_acme.db"

    def test_resolve_database_path_no_directory(self):
        """Test database path resolution without directory"""
        resolver = TenantAwareStorageResolver()
        context = TenantContext(
            tenant_id="acme",
            isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
        )
        db_path = resolver.resolve_database_path("graph.db", context)
        assert db_path == "tenant_acme.db"

    def test_resolve_database_path_custom_prefix(self):
        """Test database path resolution with custom prefix"""
        resolver = TenantAwareStorageResolver(table_prefix="org")
        context = TenantContext(
            tenant_id="acme-corp",
            isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
        )
        db_path = resolver.resolve_database_path("/var/lib/graph.db", context)
        assert db_path == "/var/lib/org_acme-corp.db"

    def test_should_filter_by_tenant_id_no_context(self):
        """Test filter determination without context"""
        resolver = TenantAwareStorageResolver()
        should_filter = resolver.should_filter_by_tenant_id(None)
        assert should_filter is False

    def test_should_filter_by_tenant_id_disabled_mode(self):
        """Test filter determination with DISABLED mode"""
        resolver = TenantAwareStorageResolver()
        context = TenantContext(
            tenant_id="acme",
            isolation_mode=TenantIsolationMode.DISABLED
        )
        should_filter = resolver.should_filter_by_tenant_id(context)
        assert should_filter is False

    def test_should_filter_by_tenant_id_shared_schema_mode(self):
        """Test filter determination with SHARED_SCHEMA mode"""
        resolver = TenantAwareStorageResolver()
        context = TenantContext(
            tenant_id="acme",
            isolation_mode=TenantIsolationMode.SHARED_SCHEMA
        )
        should_filter = resolver.should_filter_by_tenant_id(context)
        # SHARED_SCHEMA requires tenant_id column filtering
        assert should_filter is True

    def test_should_filter_by_tenant_id_separate_schema_mode(self):
        """Test filter determination with SEPARATE_SCHEMA mode"""
        resolver = TenantAwareStorageResolver()
        context = TenantContext(
            tenant_id="acme",
            isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
        )
        should_filter = resolver.should_filter_by_tenant_id(context)
        # SEPARATE_SCHEMA uses separate storage, no column filtering needed
        assert should_filter is False

    def test_validate_context_valid(self):
        """Test context validation with valid tenant_id"""
        resolver = TenantAwareStorageResolver()
        context = TenantContext(tenant_id="acme-corp-123")
        # Should not raise
        resolver.validate_context(context)

    def test_validate_context_none(self):
        """Test context validation with None context"""
        resolver = TenantAwareStorageResolver()
        # Should not raise
        resolver.validate_context(None)

    def test_validate_context_invalid_tenant_id(self):
        """Test context validation with invalid tenant_id"""
        resolver = TenantAwareStorageResolver()
        # Create context with validation disabled, then validate
        context = TenantContext(tenant_id="acme@corp", validate=False)
        with pytest.raises(InvalidTenantIdError) as exc_info:
            resolver.validate_context(context)
        assert "acme@corp" in str(exc_info.value)

    def test_multiple_table_resolutions_same_tenant(self):
        """Test resolving multiple table names for same tenant"""
        resolver = TenantAwareStorageResolver()
        context = TenantContext(
            tenant_id="acme",
            isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
        )
        
        entities_table = resolver.resolve_table_name("entities", context)
        relations_table = resolver.resolve_table_name("relations", context)
        schema_table = resolver.resolve_table_name("schema_types", context)
        
        assert entities_table == "tenant_acme_entities"
        assert relations_table == "tenant_acme_relations"
        assert schema_table == "tenant_acme_schema_types"

    def test_tenant_id_with_hyphens_and_underscores(self):
        """Test tenant IDs with allowed special characters"""
        resolver = TenantAwareStorageResolver()
        tenant_ids = [
            "acme-corp",
            "tenant_123",
            "org-123_456",
            "a1-b2_c3",
        ]
        
        for tenant_id in tenant_ids:
            context = TenantContext(
                tenant_id=tenant_id,
                isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
            )
            table_name = resolver.resolve_table_name("entities", context)
            expected = f"tenant_{tenant_id}_entities"
            assert table_name == expected

    def test_consistency_across_isolation_modes(self):
        """Test that resolver behavior is consistent across modes"""
        resolver = TenantAwareStorageResolver()
        tenant_id = "test-tenant"
        
        # Test all isolation modes
        for mode in [
            TenantIsolationMode.DISABLED,
            TenantIsolationMode.SHARED_SCHEMA,
            TenantIsolationMode.SEPARATE_SCHEMA,
        ]:
            context = TenantContext(tenant_id=tenant_id, isolation_mode=mode)
            
            # Should always return a non-empty string
            table_name = resolver.resolve_table_name("entities", context)
            assert isinstance(table_name, str)
            assert len(table_name) > 0
            
            # Schema name should be None for all except SEPARATE_SCHEMA
            schema_name = resolver.resolve_schema_name(context)
            if mode == TenantIsolationMode.SEPARATE_SCHEMA:
                assert schema_name is not None
                assert schema_name.startswith("tenant_")
            else:
                assert schema_name is None

    def test_database_path_preserves_extension(self):
        """Test that database path resolution preserves file structure"""
        resolver = TenantAwareStorageResolver()
        context = TenantContext(
            tenant_id="acme",
            isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
        )
        
        # Test various path formats
        paths = [
            ("/data/graph.db", "/data/tenant_acme.db"),
            ("/var/lib/sqlite/app.db", "/var/lib/sqlite/tenant_acme.db"),
            ("./local.db", "./tenant_acme.db"),
            ("data.db", "tenant_acme.db"),
        ]
        
        for input_path, expected_path in paths:
            result = resolver.resolve_database_path(input_path, context)
            assert result == expected_path


class TestTenantAwareStorageResolverIntegration:
    """Integration tests for resolver with realistic scenarios"""

    def test_postgresql_shared_schema_scenario(self):
        """Test resolver for PostgreSQL SHARED_SCHEMA deployment"""
        resolver = TenantAwareStorageResolver()
        context = TenantContext(
            tenant_id="acme-corp",
            isolation_mode=TenantIsolationMode.SHARED_SCHEMA
        )
        
        # Table names should be base names
        assert resolver.resolve_table_name("graph_entities", context) == "graph_entities"
        assert resolver.resolve_table_name("graph_relations", context) == "graph_relations"
        
        # No schema prefixing
        assert resolver.resolve_schema_name(context) is None
        
        # Should filter by tenant_id column
        assert resolver.should_filter_by_tenant_id(context) is True

    def test_postgresql_separate_schema_scenario(self):
        """Test resolver for PostgreSQL SEPARATE_SCHEMA deployment"""
        resolver = TenantAwareStorageResolver()
        context = TenantContext(
            tenant_id="acme-corp",
            isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
        )
        
        # Schema should be tenant-specific
        schema_name = resolver.resolve_schema_name(context)
        assert schema_name == "tenant_acme-corp"
        
        # Tables should be prefixed (for SQLite-style)
        assert resolver.resolve_table_name("entities", context) == "tenant_acme-corp_entities"
        
        # No tenant_id column filtering needed
        assert resolver.should_filter_by_tenant_id(context) is False

    def test_sqlite_shared_schema_scenario(self):
        """Test resolver for SQLite SHARED_SCHEMA deployment"""
        resolver = TenantAwareStorageResolver()
        context = TenantContext(
            tenant_id="tenant-123",
            isolation_mode=TenantIsolationMode.SHARED_SCHEMA
        )
        
        # Use same database file
        db_path = resolver.resolve_database_path("/data/graph.db", context)
        assert db_path == "/data/graph.db"
        
        # Use base table names
        assert resolver.resolve_table_name("entities", context) == "entities"
        
        # Filter by tenant_id column
        assert resolver.should_filter_by_tenant_id(context) is True

    def test_sqlite_separate_schema_scenario(self):
        """Test resolver for SQLite SEPARATE_SCHEMA deployment"""
        resolver = TenantAwareStorageResolver()
        context = TenantContext(
            tenant_id="tenant-123",
            isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
        )
        
        # Use separate database file per tenant
        db_path = resolver.resolve_database_path("/data/graph.db", context)
        assert db_path == "/data/tenant_tenant-123.db"
        
        # Tables can use base names (separate DB) or prefixed names (same DB)
        table_name = resolver.resolve_table_name("entities", context)
        assert table_name == "tenant_tenant-123_entities"
        
        # No column filtering needed
        assert resolver.should_filter_by_tenant_id(context) is False

    def test_migration_scenario(self):
        """Test resolver during migration from single to multi-tenant"""
        resolver = TenantAwareStorageResolver()
        
        # Phase 1: Single-tenant (no context)
        table_name = resolver.resolve_table_name("entities", None)
        assert table_name == "entities"
        
        # Phase 2: Add multi-tenancy with SHARED_SCHEMA (backward compatible)
        context_shared = TenantContext(
            tenant_id="default",
            isolation_mode=TenantIsolationMode.SHARED_SCHEMA
        )
        table_name = resolver.resolve_table_name("entities", context_shared)
        assert table_name == "entities"  # Same table, filtered by tenant_id
        
        # Phase 3: New tenants use SEPARATE_SCHEMA for isolation
        context_separate = TenantContext(
            tenant_id="new-tenant",
            isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
        )
        table_name = resolver.resolve_table_name("entities", context_separate)
        assert table_name == "tenant_new-tenant_entities"  # Isolated storage
