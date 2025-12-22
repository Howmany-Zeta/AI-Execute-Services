"""
Unit tests for SchemaManager Multi-Tenancy Support

Tests tenant-scoped schema operations, cache management, and fallback behavior.
"""

import pytest
from aiecs.domain.knowledge_graph.schema.property_schema import PropertySchema, PropertyType
from aiecs.domain.knowledge_graph.schema.entity_type import EntityType
from aiecs.domain.knowledge_graph.schema.relation_type import RelationType
from aiecs.domain.knowledge_graph.schema.graph_schema import GraphSchema
from aiecs.domain.knowledge_graph.schema.schema_manager import SchemaManager


class TestSchemaManagerTenantBasics:
    """Test basic tenant-scoped operations"""

    def test_register_entity_type_global(self):
        """Test registering entity type in global schema"""
        manager = SchemaManager()
        person_type = EntityType(name="Person", description="A person")

        manager.register_entity_type(person_type)

        assert "Person" in manager.list_entity_types()
        assert manager.get_entity_type("Person") is not None
        assert manager.get_entity_type("Person").description == "A person"

    def test_register_entity_type_tenant_scoped(self):
        """Test registering entity type in tenant-specific schema"""
        manager = SchemaManager()
        tenant_person = EntityType(name="Person", description="Tenant-specific person")

        manager.register_entity_type(tenant_person, tenant_id="tenant-a")

        # Should exist in tenant schema
        result = manager.get_entity_type("Person", tenant_id="tenant-a")
        assert result is not None
        assert result.description == "Tenant-specific person"

        # Should not exist in global schema (unless we also register it there)
        global_result = manager.get_entity_type("Person", tenant_id=None)
        assert global_result is None

    def test_get_entity_type_with_fallback(self):
        """Test that tenant queries fall back to global schema"""
        manager = SchemaManager()
        global_person = EntityType(name="Person", description="Global person")

        # Register in global schema
        manager.register_entity_type(global_person, tenant_id=None)

        # Query from tenant that doesn't have this type - should fall back to global
        result = manager.get_entity_type("Person", tenant_id="tenant-b")
        assert result is not None
        assert result.description == "Global person"

    def test_tenant_override_global_type(self):
        """Test that tenant-specific types override global types"""
        manager = SchemaManager()
        global_person = EntityType(name="Person", description="Global person")
        tenant_person = EntityType(name="Person", description="Tenant person")

        # Register both
        manager.register_entity_type(global_person, tenant_id=None)
        manager.register_entity_type(tenant_person, tenant_id="tenant-c")

        # Global query should return global
        global_result = manager.get_entity_type("Person", tenant_id=None)
        assert global_result.description == "Global person"

        # Tenant query should return tenant-specific
        tenant_result = manager.get_entity_type("Person", tenant_id="tenant-c")
        assert tenant_result.description == "Tenant person"

    def test_create_entity_type_tenant_scoped(self):
        """Test create_entity_type with tenant_id parameter"""
        manager = SchemaManager()
        company_type = EntityType(name="Company", description="Tenant company")

        manager.create_entity_type(company_type, tenant_id="tenant-d")

        result = manager.get_entity_type("Company", tenant_id="tenant-d")
        assert result is not None
        assert result.description == "Tenant company"


class TestSchemaManagerTenantRelationTypes:
    """Test tenant-scoped relation type operations"""

    def test_create_relation_type_tenant_scoped(self):
        """Test creating relation type in tenant schema"""
        manager = SchemaManager()
        works_for = RelationType(
            name="WORKS_FOR",
            description="Employment",
            source_entity_types=["Person"],
            target_entity_types=["Company"]
        )

        manager.create_relation_type(works_for, tenant_id="tenant-e")

        result = manager.get_relation_type("WORKS_FOR", tenant_id="tenant-e")
        assert result is not None
        assert result.description == "Employment"

    def test_get_relation_type_with_fallback(self):
        """Test relation type fallback to global schema"""
        manager = SchemaManager()
        global_rel = RelationType(name="KNOWS", description="Global knows")

        manager.create_relation_type(global_rel, tenant_id=None)

        # Query from tenant - should fall back
        result = manager.get_relation_type("KNOWS", tenant_id="tenant-f")
        assert result is not None
        assert result.description == "Global knows"

    def test_update_relation_type_tenant_scoped(self):
        """Test updating relation type in tenant schema"""
        manager = SchemaManager()
        original = RelationType(name="MANAGES", description="Original")
        updated = RelationType(name="MANAGES", description="Updated")

        manager.create_relation_type(original, tenant_id="tenant-g")
        manager.update_relation_type(updated, tenant_id="tenant-g")

        result = manager.get_relation_type("MANAGES", tenant_id="tenant-g")
        assert result.description == "Updated"

    def test_delete_relation_type_tenant_scoped(self):
        """Test deleting relation type from tenant schema"""
        manager = SchemaManager()
        rel = RelationType(name="REPORTS_TO")

        manager.create_relation_type(rel, tenant_id="tenant-h")
        assert manager.get_relation_type("REPORTS_TO", tenant_id="tenant-h") is not None

        manager.delete_relation_type("REPORTS_TO", tenant_id="tenant-h")
        
        # Should not exist in tenant schema
        assert manager.get_relation_type("REPORTS_TO", tenant_id="tenant-h") is None


class TestSchemaManagerTenantListOperations:
    """Test listing types with tenant context"""

    def test_list_entity_types_global(self):
        """Test listing global entity types"""
        manager = SchemaManager()
        manager.create_entity_type(EntityType(name="Person"), tenant_id=None)
        manager.create_entity_type(EntityType(name="Company"), tenant_id=None)

        types = manager.list_entity_types(tenant_id=None)
        assert "Person" in types
        assert "Company" in types
        assert len(types) == 2

    def test_list_entity_types_tenant_includes_global(self):
        """Test that tenant listing includes global types"""
        manager = SchemaManager()
        manager.create_entity_type(EntityType(name="Person"), tenant_id=None)
        manager.create_entity_type(EntityType(name="TenantSpecific"), tenant_id="tenant-i")

        types = manager.list_entity_types(tenant_id="tenant-i")
        
        # Should include both global and tenant-specific
        assert "Person" in types
        assert "TenantSpecific" in types

    def test_list_entity_types_tenant_without_custom_types(self):
        """Test tenant listing when tenant has no custom types"""
        manager = SchemaManager()
        manager.create_entity_type(EntityType(name="GlobalType"), tenant_id=None)

        types = manager.list_entity_types(tenant_id="tenant-j")
        
        # Should only show global types
        assert "GlobalType" in types

    def test_list_relation_types_tenant_includes_global(self):
        """Test that tenant listing includes global relation types"""
        manager = SchemaManager()
        manager.create_relation_type(RelationType(name="GLOBAL_REL"), tenant_id=None)
        manager.create_relation_type(RelationType(name="TENANT_REL"), tenant_id="tenant-k")

        types = manager.list_relation_types(tenant_id="tenant-k")
        
        assert "GLOBAL_REL" in types
        assert "TENANT_REL" in types


class TestSchemaManagerTenantCaching:
    """Test tenant-scoped cache operations"""

    def test_cache_with_tenant_scoped_keys(self):
        """Test that cache uses tenant-scoped keys"""
        manager = SchemaManager(enable_cache=True)
        
        # Create different types for different tenants
        manager.create_entity_type(
            EntityType(name="Person", description="Tenant A"),
            tenant_id="tenant-a"
        )
        manager.create_entity_type(
            EntityType(name="Person", description="Tenant B"),
            tenant_id="tenant-b"
        )

        # Both should be cached separately
        result_a = manager.get_entity_type("Person", tenant_id="tenant-a")
        result_b = manager.get_entity_type("Person", tenant_id="tenant-b")

        assert result_a.description == "Tenant A"
        assert result_b.description == "Tenant B"

    def test_cache_hit_for_tenant_types(self):
        """Test cache hits for tenant-specific types"""
        manager = SchemaManager(enable_cache=True)
        entity_type = EntityType(name="Product", description="Tenant product")

        manager.create_entity_type(entity_type, tenant_id="tenant-cache")

        # First access (cache miss)
        result1 = manager.get_entity_type("Product", tenant_id="tenant-cache")
        
        # Second access (should be cache hit)
        result2 = manager.get_entity_type("Product", tenant_id="tenant-cache")

        assert result1 is not None
        assert result2 is not None
        assert result1.description == result2.description

    def test_invalidate_cache_tenant_specific(self):
        """Test invalidating cache for specific tenant"""
        manager = SchemaManager(enable_cache=True)
        
        manager.create_entity_type(EntityType(name="Type1"), tenant_id="tenant-m")
        manager.create_entity_type(EntityType(name="Type2"), tenant_id="tenant-n")

        # Access both to cache them
        manager.get_entity_type("Type1", tenant_id="tenant-m")
        manager.get_entity_type("Type2", tenant_id="tenant-n")

        # Invalidate only tenant-m
        manager.invalidate_cache(tenant_id="tenant-m")

        # Both should still be accessible (from storage)
        assert manager.get_entity_type("Type1", tenant_id="tenant-m") is not None
        assert manager.get_entity_type("Type2", tenant_id="tenant-n") is not None

    def test_invalidate_cache_all_tenants(self):
        """Test invalidating cache for all tenants"""
        manager = SchemaManager(enable_cache=True)
        
        manager.create_entity_type(EntityType(name="Type1"), tenant_id="tenant-o")
        manager.create_entity_type(EntityType(name="Type2"), tenant_id=None)

        # Cache them
        manager.get_entity_type("Type1", tenant_id="tenant-o")
        manager.get_entity_type("Type2", tenant_id=None)

        # Invalidate all
        manager.invalidate_cache(tenant_id="*")

        # All should still be accessible
        assert manager.get_entity_type("Type1", tenant_id="tenant-o") is not None
        assert manager.get_entity_type("Type2", tenant_id=None) is not None

    def test_invalidate_specific_type_tenant_scoped(self):
        """Test invalidating specific type in tenant cache"""
        manager = SchemaManager(enable_cache=True)
        
        manager.create_entity_type(EntityType(name="Product"), tenant_id="tenant-p")
        manager.create_entity_type(EntityType(name="Service"), tenant_id="tenant-p")

        # Cache both
        manager.get_entity_type("Product", tenant_id="tenant-p")
        manager.get_entity_type("Service", tenant_id="tenant-p")

        # Invalidate only Product
        manager.invalidate_cache(type_name="Product", tenant_id="tenant-p")

        # Both should still be accessible
        assert manager.get_entity_type("Product", tenant_id="tenant-p") is not None
        assert manager.get_entity_type("Service", tenant_id="tenant-p") is not None


class TestSchemaManagerTenantUpdateDelete:
    """Test update and delete operations with tenant context"""

    def test_update_entity_type_tenant_scoped(self):
        """Test updating entity type in tenant schema"""
        manager = SchemaManager()
        original = EntityType(name="Person", description="Original")
        updated = EntityType(name="Person", description="Updated")

        manager.create_entity_type(original, tenant_id="tenant-q")
        manager.update_entity_type(updated, tenant_id="tenant-q")

        result = manager.get_entity_type("Person", tenant_id="tenant-q")
        assert result.description == "Updated"

    def test_delete_entity_type_tenant_scoped(self):
        """Test deleting entity type from tenant schema"""
        manager = SchemaManager()
        entity_type = EntityType(name="TempType")

        manager.create_entity_type(entity_type, tenant_id="tenant-r")
        assert manager.get_entity_type("TempType", tenant_id="tenant-r") is not None

        manager.delete_entity_type("TempType", tenant_id="tenant-r")
        
        # Should not exist in tenant schema anymore
        # Note: If it exists in global, fallback will still return it
        assert manager.get_entity_type("TempType", tenant_id="tenant-r") is None

    def test_delete_tenant_type_does_not_affect_global(self):
        """Test that deleting tenant type doesn't affect global"""
        manager = SchemaManager()
        global_type = EntityType(name="SharedType", description="Global")
        tenant_type = EntityType(name="SharedType", description="Tenant")

        manager.create_entity_type(global_type, tenant_id=None)
        manager.create_entity_type(tenant_type, tenant_id="tenant-s")

        # Delete from tenant
        manager.delete_entity_type("SharedType", tenant_id="tenant-s")

        # Global should still exist
        global_result = manager.get_entity_type("SharedType", tenant_id=None)
        assert global_result is not None
        assert global_result.description == "Global"

        # Tenant should fall back to global
        tenant_result = manager.get_entity_type("SharedType", tenant_id="tenant-s")
        assert tenant_result is not None
        assert tenant_result.description == "Global"


class TestSchemaManagerTenantIsolation:
    """Test tenant isolation guarantees"""

    def test_tenant_types_isolated_from_each_other(self):
        """Test that different tenants can't see each other's types"""
        manager = SchemaManager()
        
        manager.create_entity_type(
            EntityType(name="PrivateType", description="Tenant A private"),
            tenant_id="tenant-a"
        )
        manager.create_entity_type(
            EntityType(name="PrivateType", description="Tenant B private"),
            tenant_id="tenant-b"
        )

        # Each tenant should see their own version
        result_a = manager.get_entity_type("PrivateType", tenant_id="tenant-a")
        result_b = manager.get_entity_type("PrivateType", tenant_id="tenant-b")

        assert result_a.description == "Tenant A private"
        assert result_b.description == "Tenant B private"

    def test_multiple_tenants_independent_schemas(self):
        """Test that multiple tenants maintain independent schemas"""
        manager = SchemaManager()

        # Tenant A: Person and Company
        manager.create_entity_type(EntityType(name="Person"), tenant_id="tenant-x")
        manager.create_entity_type(EntityType(name="Company"), tenant_id="tenant-x")

        # Tenant B: Only Product
        manager.create_entity_type(EntityType(name="Product"), tenant_id="tenant-y")

        # Tenant A should have Person and Company
        types_x = manager.list_entity_types(tenant_id="tenant-x")
        assert "Person" in types_x
        assert "Company" in types_x

        # Tenant B should have Product (and not see tenant A's types unless global)
        types_y = manager.list_entity_types(tenant_id="tenant-y")
        assert "Product" in types_y


class TestSchemaManagerTenantEdgeCases:
    """Test edge cases and error conditions"""

    def test_get_nonexistent_type_tenant_no_fallback(self):
        """Test getting non-existent type with no global fallback"""
        manager = SchemaManager()
        
        result = manager.get_entity_type("NonExistent", tenant_id="tenant-z")
        assert result is None

    def test_update_nonexistent_tenant_type(self):
        """Test updating type that doesn't exist in tenant schema"""
        manager = SchemaManager()
        
        with pytest.raises(ValueError):
            manager.update_entity_type(
                EntityType(name="NonExistent"),
                tenant_id="tenant-fail"
            )

    def test_delete_nonexistent_tenant_type(self):
        """Test deleting type that doesn't exist in tenant schema"""
        manager = SchemaManager()
        
        with pytest.raises(ValueError):
            manager.delete_entity_type("NonExistent", tenant_id="tenant-fail2")

    def test_cache_with_none_tenant_id(self):
        """Test that None tenant_id works correctly with cache"""
        manager = SchemaManager(enable_cache=True)
        
        manager.create_entity_type(EntityType(name="GlobalCached"), tenant_id=None)
        
        # First access
        result1 = manager.get_entity_type("GlobalCached", tenant_id=None)
        # Second access (cached)
        result2 = manager.get_entity_type("GlobalCached", tenant_id=None)
        
        assert result1 is not None
        assert result2 is not None
        assert result1.name == result2.name


class TestSchemaManagerTenantCacheInvalidation:
    """Test detailed cache invalidation scenarios"""

    def test_invalidate_global_cache_only(self):
        """Test invalidating only global cache entries"""
        manager = SchemaManager(enable_cache=True)
        
        manager.create_entity_type(EntityType(name="Global1"), tenant_id=None)
        manager.create_entity_type(EntityType(name="Tenant1"), tenant_id="tenant-aa")

        # Cache both
        manager.get_entity_type("Global1", tenant_id=None)
        manager.get_entity_type("Tenant1", tenant_id="tenant-aa")

        # Invalidate only global (tenant_id=None)
        manager.invalidate_cache(tenant_id=None)

        # Both should still be accessible
        assert manager.get_entity_type("Global1", tenant_id=None) is not None
        assert manager.get_entity_type("Tenant1", tenant_id="tenant-aa") is not None

    def test_cache_key_generation(self):
        """Test internal cache key generation"""
        manager = SchemaManager(enable_cache=True)
        
        # Create types with same name in different tenants
        manager.create_entity_type(EntityType(name="Same"), tenant_id=None)
        manager.create_entity_type(EntityType(name="Same", description="T1"), tenant_id="t1")
        manager.create_entity_type(EntityType(name="Same", description="T2"), tenant_id="t2")

        # All should be independently cached
        global_same = manager.get_entity_type("Same", tenant_id=None)
        t1_same = manager.get_entity_type("Same", tenant_id="t1")
        t2_same = manager.get_entity_type("Same", tenant_id="t2")

        assert global_same.description is None or global_same.description == ""
        assert t1_same.description == "T1"
        assert t2_same.description == "T2"


class TestSchemaManagerBackwardCompatibility:
    """Test backward compatibility with non-tenant code"""

    def test_old_api_without_tenant_id_works(self):
        """Test that old API calls without tenant_id still work"""
        manager = SchemaManager()
        
        # Old-style calls (no tenant_id)
        manager.create_entity_type(EntityType(name="Person"))
        assert manager.get_entity_type("Person") is not None
        assert "Person" in manager.list_entity_types()
        
        manager.update_entity_type(EntityType(name="Person", description="Updated"))
        assert manager.get_entity_type("Person").description == "Updated"
        
        manager.delete_entity_type("Person")
        assert manager.get_entity_type("Person") is None

    def test_mixing_tenant_and_global_operations(self):
        """Test mixing tenant and global operations"""
        manager = SchemaManager()
        
        # Global operations
        manager.create_entity_type(EntityType(name="Global1"))
        
        # Tenant operations
        manager.create_entity_type(EntityType(name="Tenant1"), tenant_id="mixed-tenant")
        
        # Both should work
        assert manager.get_entity_type("Global1") is not None
        assert manager.get_entity_type("Tenant1", tenant_id="mixed-tenant") is not None
        
        # Tenant can see global via fallback
        assert manager.get_entity_type("Global1", tenant_id="mixed-tenant") is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
