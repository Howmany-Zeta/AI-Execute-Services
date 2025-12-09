"""
Schema Manager

Service for managing knowledge graph schemas with CRUD operations.
Supports multi-tenancy with tenant-scoped schemas and global fallback.
"""

from typing import Optional, List, Dict, Any, Type
from enum import Enum
import json
from pathlib import Path
from aiecs.domain.knowledge_graph.schema.graph_schema import GraphSchema
from aiecs.domain.knowledge_graph.schema.entity_type import EntityType
from aiecs.domain.knowledge_graph.schema.relation_type import RelationType
from aiecs.domain.knowledge_graph.schema.property_schema import PropertySchema
from aiecs.domain.knowledge_graph.schema.type_enums import TypeEnumGenerator
from aiecs.infrastructure.graph_storage.schema_cache import LRUCache
from aiecs.infrastructure.graph_storage.tenant import TenantContext


class SchemaManager:
    """
    Schema Manager Service

    Manages knowledge graph schemas with support for:
    - Creating, reading, updating, deleting entity and relation types
    - Schema persistence (save/load from JSON)
    - Schema validation
    - Transaction-like operations (commit/rollback)
    - LRU caching with TTL for performance optimization

    Example:
        ```python
        manager = SchemaManager(cache_size=1000, ttl_seconds=3600)

        # Add entity type
        person_type = EntityType(name="Person", ...)
        manager.create_entity_type(person_type)

        # Get entity type (cached)
        person = manager.get_entity_type("Person")

        # Check cache stats
        stats = manager.get_cache_stats()
        print(f"Cache hit rate: {stats['hit_rate']:.2%}")

        # Save schema
        manager.save("./schema.json")
        ```
    """

    def __init__(
        self,
        schema: Optional[GraphSchema] = None,
        cache_size: int = 1000,
        ttl_seconds: Optional[int] = 3600,
        enable_cache: bool = True,
    ):
        """
        Initialize schema manager with multi-tenancy support

        Args:
            schema: Initial global schema (default: empty schema)
            cache_size: Maximum cache size (default: 1000)
            ttl_seconds: Cache TTL in seconds (default: 3600, None = no expiration)
            enable_cache: Whether to enable caching (default: True)
        """
        # Global schema (tenant_id=None)
        self.schema = schema if schema is not None else GraphSchema()
        self._transaction_schema: Optional[GraphSchema] = None

        # Tenant-scoped schemas: tenant_id -> GraphSchema
        self._tenant_schemas: Dict[str, GraphSchema] = {}

        # Initialize caches
        self._enable_cache = enable_cache
        # Declare cache variables as Optional before if/else to avoid type conflicts
        self._entity_type_cache: Optional[LRUCache[EntityType]]
        self._relation_type_cache: Optional[LRUCache[RelationType]]
        self._property_cache: Optional[LRUCache[PropertySchema]]
        if enable_cache:
            self._entity_type_cache = LRUCache(max_size=cache_size, ttl_seconds=ttl_seconds)
            self._relation_type_cache = LRUCache(max_size=cache_size, ttl_seconds=ttl_seconds)
            self._property_cache = LRUCache(max_size=cache_size, ttl_seconds=ttl_seconds)
        else:
            self._entity_type_cache = None
            self._relation_type_cache = None
            self._property_cache = None

    def _get_schema(self, tenant_id: Optional[str] = None) -> GraphSchema:
        """
        Get schema for a specific tenant (with fallback to global)

        Args:
            tenant_id: Tenant ID (None = global schema)

        Returns:
            GraphSchema for the tenant (or global if tenant schema doesn't exist)
        """
        if tenant_id is None:
            return self.schema

        # Return tenant-specific schema if it exists, otherwise use global
        return self._tenant_schemas.get(tenant_id, self.schema)

    def _ensure_tenant_schema(self, tenant_id: str) -> GraphSchema:
        """
        Ensure a tenant-specific schema exists (creates if needed)

        Args:
            tenant_id: Tenant ID

        Returns:
            Tenant-specific GraphSchema

        Note:
            Creates an empty schema for the tenant. Global types are accessible
            via fallback mechanism in get_entity_type/get_relation_type methods.
        """
        if tenant_id not in self._tenant_schemas:
            # Create new empty schema for tenant
            # Fallback to global schema happens in get methods
            self._tenant_schemas[tenant_id] = GraphSchema()

        return self._tenant_schemas[tenant_id]

    def _make_cache_key(self, type_name: str, tenant_id: Optional[str] = None) -> str:
        """
        Create cache key with tenant scope

        Args:
            type_name: Type name
            tenant_id: Tenant ID (None = global)

        Returns:
            Cache key string
        """
        if tenant_id is None:
            return type_name
        return f"{tenant_id}:{type_name}"

    # Entity Type Operations

    def create_entity_type(self, entity_type: EntityType, tenant_id: Optional[str] = None) -> None:
        """
        Create a new entity type (tenant-scoped or global)

        Args:
            entity_type: Entity type to create
            tenant_id: Tenant ID for tenant-scoped schema (None = global)

        Raises:
            ValueError: If entity type already exists

        Note:
            Tenant schemas are independent from global schema. The same type name
            can exist in both global and tenant schemas with different definitions.
        """
        schema = self._ensure_tenant_schema(tenant_id) if tenant_id else self.schema
        
        # Safety check: ensure tenant schema is not the global schema
        if tenant_id is not None and schema is self.schema:
            raise RuntimeError(f"Internal error: tenant schema for '{tenant_id}' is referencing global schema")
        
        schema.add_entity_type(entity_type)

        # Cache the new entity type with tenant-scoped key
        if self._enable_cache and self._entity_type_cache:
            cache_key = self._make_cache_key(entity_type.name, tenant_id)
            self._entity_type_cache.set(cache_key, entity_type)

    def register_entity_type(self, entity_type: EntityType, tenant_id: Optional[str] = None) -> None:
        """
        Register a new entity type (alias for create_entity_type)

        Args:
            entity_type: Entity type to register
            tenant_id: Tenant ID for tenant-scoped schema (None = global)

        Raises:
            ValueError: If entity type already exists
        """
        self.create_entity_type(entity_type, tenant_id=tenant_id)

    def update_entity_type(self, entity_type: EntityType, tenant_id: Optional[str] = None) -> None:
        """
        Update an existing entity type (tenant-scoped or global)

        Args:
            entity_type: Updated entity type
            tenant_id: Tenant ID for tenant-scoped schema (None = global)

        Raises:
            ValueError: If entity type doesn't exist
        """
        schema = self._get_schema(tenant_id)
        schema.update_entity_type(entity_type)

        # Invalidate cache for this entity type
        if self._enable_cache and self._entity_type_cache:
            cache_key = self._make_cache_key(entity_type.name, tenant_id)
            self._entity_type_cache.delete(cache_key)

    def delete_entity_type(self, type_name: str, tenant_id: Optional[str] = None) -> None:
        """
        Delete an entity type (tenant-scoped or global)

        Args:
            type_name: Name of entity type to delete
            tenant_id: Tenant ID for tenant-scoped schema (None = global)

        Raises:
            ValueError: If entity type doesn't exist or is in use
        """
        schema = self._get_schema(tenant_id)
        schema.delete_entity_type(type_name)

        # Invalidate cache for this entity type
        if self._enable_cache and self._entity_type_cache:
            cache_key = self._make_cache_key(type_name, tenant_id)
            self._entity_type_cache.delete(cache_key)

    def get_entity_type(self, type_name: str, tenant_id: Optional[str] = None) -> Optional[EntityType]:
        """
        Get an entity type by name (with caching and tenant-scoped fallback)

        Args:
            type_name: Name of entity type
            tenant_id: Tenant ID for tenant-scoped schema (None = global)

        Returns:
            Entity type or None if not found

        Note:
            Falls back to global schema if tenant schema doesn't have the type
        """
        cache_key = self._make_cache_key(type_name, tenant_id)

        # Try cache first
        if self._enable_cache and self._entity_type_cache:
            cached = self._entity_type_cache.get(cache_key)
            if cached is not None:
                return cached

        # Load from tenant schema first
        if tenant_id is not None:
            tenant_schema = self._tenant_schemas.get(tenant_id)
            if tenant_schema is not None:
                entity_type = tenant_schema.get_entity_type(type_name)
                if entity_type is not None:
                    # Cache the tenant-specific result
                    if self._enable_cache and self._entity_type_cache:
                        self._entity_type_cache.set(cache_key, entity_type)
                    return entity_type

        # Fall back to global schema
        entity_type = self.schema.get_entity_type(type_name)

        # Cache the result if found
        if entity_type is not None and self._enable_cache and self._entity_type_cache:
            self._entity_type_cache.set(cache_key, entity_type)

        return entity_type

    def list_entity_types(self, tenant_id: Optional[str] = None) -> List[str]:
        """
        List all entity type names (tenant-scoped or global)

        Args:
            tenant_id: Tenant ID for tenant-scoped schema (None = global)

        Returns:
            List of entity type names (includes tenant-specific + global if tenant_id provided)

        Note:
            When tenant_id is provided, returns union of tenant-specific and global types
        """
        schema = self._get_schema(tenant_id)
        tenant_types = set(schema.get_entity_type_names())

        # If querying tenant schema, also include global types (fallback)
        if tenant_id is not None and tenant_id in self._tenant_schemas:
            global_types = set(self.schema.get_entity_type_names())
            tenant_types.update(global_types)

        return sorted(list(tenant_types))

    # Relation Type Operations

    def create_relation_type(self, relation_type: RelationType, tenant_id: Optional[str] = None) -> None:
        """
        Create a new relation type (tenant-scoped or global)

        Args:
            relation_type: Relation type to create
            tenant_id: Tenant ID for tenant-scoped schema (None = global)

        Raises:
            ValueError: If relation type already exists
        """
        schema = self._ensure_tenant_schema(tenant_id) if tenant_id else self.schema
        schema.add_relation_type(relation_type)

        # Cache the new relation type with tenant-scoped key
        if self._enable_cache and self._relation_type_cache:
            cache_key = self._make_cache_key(relation_type.name, tenant_id)
            self._relation_type_cache.set(cache_key, relation_type)

    def update_relation_type(self, relation_type: RelationType, tenant_id: Optional[str] = None) -> None:
        """
        Update an existing relation type (tenant-scoped or global)

        Args:
            relation_type: Updated relation type
            tenant_id: Tenant ID for tenant-scoped schema (None = global)

        Raises:
            ValueError: If relation type doesn't exist
        """
        schema = self._get_schema(tenant_id)
        schema.update_relation_type(relation_type)

        # Invalidate cache for this relation type
        if self._enable_cache and self._relation_type_cache:
            cache_key = self._make_cache_key(relation_type.name, tenant_id)
            self._relation_type_cache.delete(cache_key)

    def delete_relation_type(self, type_name: str, tenant_id: Optional[str] = None) -> None:
        """
        Delete a relation type (tenant-scoped or global)

        Args:
            type_name: Name of relation type to delete
            tenant_id: Tenant ID for tenant-scoped schema (None = global)

        Raises:
            ValueError: If relation type doesn't exist
        """
        schema = self._get_schema(tenant_id)
        schema.delete_relation_type(type_name)

        # Invalidate cache for this relation type
        if self._enable_cache and self._relation_type_cache:
            cache_key = self._make_cache_key(type_name, tenant_id)
            self._relation_type_cache.delete(cache_key)

    def get_relation_type(self, type_name: str, tenant_id: Optional[str] = None) -> Optional[RelationType]:
        """
        Get a relation type by name (with caching and tenant-scoped fallback)

        Args:
            type_name: Name of relation type
            tenant_id: Tenant ID for tenant-scoped schema (None = global)

        Returns:
            Relation type or None if not found

        Note:
            Falls back to global schema if tenant schema doesn't have the type
        """
        cache_key = self._make_cache_key(type_name, tenant_id)

        # Try cache first
        if self._enable_cache and self._relation_type_cache:
            cached = self._relation_type_cache.get(cache_key)
            if cached is not None:
                return cached

        # Load from tenant schema first
        if tenant_id is not None:
            tenant_schema = self._tenant_schemas.get(tenant_id)
            if tenant_schema is not None:
                relation_type = tenant_schema.get_relation_type(type_name)
                if relation_type is not None:
                    # Cache the tenant-specific result
                    if self._enable_cache and self._relation_type_cache:
                        self._relation_type_cache.set(cache_key, relation_type)
                    return relation_type

        # Fall back to global schema
        relation_type = self.schema.get_relation_type(type_name)

        # Cache the result if found
        if relation_type is not None and self._enable_cache and self._relation_type_cache:
            self._relation_type_cache.set(cache_key, relation_type)

        return relation_type

    def list_relation_types(self, tenant_id: Optional[str] = None) -> List[str]:
        """
        List all relation type names (tenant-scoped or global)

        Args:
            tenant_id: Tenant ID for tenant-scoped schema (None = global)

        Returns:
            List of relation type names (includes tenant-specific + global if tenant_id provided)

        Note:
            When tenant_id is provided, returns union of tenant-specific and global types
        """
        schema = self._get_schema(tenant_id)
        tenant_types = set(schema.get_relation_type_names())

        # If querying tenant schema, also include global types (fallback)
        if tenant_id is not None and tenant_id in self._tenant_schemas:
            global_types = set(self.schema.get_relation_type_names())
            tenant_types.update(global_types)

        return sorted(list(tenant_types))

    # Schema Validation

    def validate_entity(self, entity_type_name: str, properties: dict) -> bool:
        """
        Validate entity properties against schema

        Args:
            entity_type_name: Name of entity type
            properties: Dictionary of properties to validate

        Returns:
            True if validation passes

        Raises:
            ValueError: If validation fails
        """
        entity_type = self.get_entity_type(entity_type_name)
        if entity_type is None:
            raise ValueError(f"Entity type '{entity_type_name}' not found in schema")

        return entity_type.validate_properties(properties)

    def validate_relation(
        self,
        relation_type_name: str,
        source_entity_type: str,
        target_entity_type: str,
        properties: dict,
    ) -> bool:
        """
        Validate relation against schema

        Args:
            relation_type_name: Name of relation type
            source_entity_type: Source entity type name
            target_entity_type: Target entity type name
            properties: Dictionary of properties to validate

        Returns:
            True if validation passes

        Raises:
            ValueError: If validation fails
        """
        relation_type = self.get_relation_type(relation_type_name)
        if relation_type is None:
            raise ValueError(f"Relation type '{relation_type_name}' not found in schema")

        # Validate entity types
        relation_type.validate_entity_types(source_entity_type, target_entity_type)

        # Validate properties
        return relation_type.validate_properties(properties)

    # Schema Persistence

    def save(self, file_path: str) -> None:
        """
        Save schema to JSON file

        Args:
            file_path: Path to save schema
        """
        schema_dict = self.schema.model_dump(mode="json")

        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(schema_dict, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, file_path: str) -> "SchemaManager":
        """
        Load schema from JSON file

        Args:
            file_path: Path to load schema from

        Returns:
            New SchemaManager instance with loaded schema
        """
        with open(file_path, "r", encoding="utf-8") as f:
            schema_dict = json.load(f)

        schema = GraphSchema(**schema_dict)
        return cls(schema=schema)

    # Transaction Support (Simple)

    def begin_transaction(self) -> None:
        """Begin a schema transaction"""
        # Create a deep copy of the current schema
        schema_json = self.schema.model_dump_json()
        self._transaction_schema = GraphSchema(**json.loads(schema_json))

    def commit(self) -> None:
        """Commit the current transaction"""
        self._transaction_schema = None

    def rollback(self) -> None:
        """
        Rollback to the state at transaction start

        Raises:
            RuntimeError: If no transaction is active
        """
        if self._transaction_schema is None:
            raise RuntimeError("No active transaction to rollback")

        self.schema = self._transaction_schema
        self._transaction_schema = None

    @property
    def is_in_transaction(self) -> bool:
        """Check if a transaction is active"""
        return self._transaction_schema is not None

    # Cache Management

    def invalidate_cache(self, type_name: Optional[str] = None, tenant_id: Optional[str] = None) -> None:
        """
        Invalidate cache entries (tenant-scoped or global)

        Args:
            type_name: Specific type to invalidate (None = invalidate all)
            tenant_id: Tenant ID for tenant-scoped invalidation (None = global, "*" = all tenants)
        """
        if not self._enable_cache:
            return

        if type_name is None:
            if tenant_id == "*":
                # Clear all caches (all tenants)
                if self._entity_type_cache:
                    self._entity_type_cache.clear()
                if self._relation_type_cache:
                    self._relation_type_cache.clear()
                if self._property_cache:
                    self._property_cache.clear()
            elif tenant_id is not None:
                # Clear only entries for specific tenant
                self._invalidate_tenant_cache(tenant_id)
            else:
                # Clear global cache entries only
                if self._entity_type_cache:
                    # Clear only non-tenant keys (no ":" in key)
                    for key in list(self._entity_type_cache._cache.keys()):
                        if ":" not in key:
                            self._entity_type_cache.delete(key)
                if self._relation_type_cache:
                    for key in list(self._relation_type_cache._cache.keys()):
                        if ":" not in key:
                            self._relation_type_cache.delete(key)
        else:
            # Invalidate specific type with tenant scope
            cache_key = self._make_cache_key(type_name, tenant_id)
            if self._entity_type_cache:
                self._entity_type_cache.delete(cache_key)
            if self._relation_type_cache:
                self._relation_type_cache.delete(cache_key)

    def _invalidate_tenant_cache(self, tenant_id: str) -> None:
        """
        Invalidate all cache entries for a specific tenant

        Args:
            tenant_id: Tenant ID to invalidate
        """
        if not self._enable_cache:
            return

        tenant_prefix = f"{tenant_id}:"

        # Remove all cache entries with this tenant prefix
        if self._entity_type_cache:
            for key in list(self._entity_type_cache._cache.keys()):
                if key.startswith(tenant_prefix):
                    self._entity_type_cache.delete(key)

        if self._relation_type_cache:
            for key in list(self._relation_type_cache._cache.keys()):
                if key.startswith(tenant_prefix):
                    self._relation_type_cache.delete(key)

        if self._property_cache:
            for key in list(self._property_cache._cache.keys()):
                if key.startswith(tenant_prefix):
                    self._property_cache.delete(key)

    def cleanup_expired_cache(self) -> Dict[str, int]:
        """
        Remove expired cache entries

        Returns:
            Dictionary with number of entries removed per cache
        """
        if not self._enable_cache:
            return {"entity_types": 0, "relation_types": 0, "properties": 0}

        return {
            "entity_types": (self._entity_type_cache.cleanup_expired() if self._entity_type_cache else 0),
            "relation_types": (self._relation_type_cache.cleanup_expired() if self._relation_type_cache else 0),
            "properties": (self._property_cache.cleanup_expired() if self._property_cache else 0),
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache statistics for all caches
        """
        if not self._enable_cache:
            return {
                "enabled": False,
                "entity_types": {},
                "relation_types": {},
                "properties": {},
            }

        return {
            "enabled": True,
            "entity_types": (self._entity_type_cache.get_stats() if self._entity_type_cache else {}),
            "relation_types": (self._relation_type_cache.get_stats() if self._relation_type_cache else {}),
            "properties": (self._property_cache.get_stats() if self._property_cache else {}),
        }

    def reset_cache_metrics(self) -> None:
        """Reset cache metrics (hits, misses, etc.)"""
        if not self._enable_cache:
            return

        if self._entity_type_cache:
            self._entity_type_cache.reset_metrics()
        if self._relation_type_cache:
            self._relation_type_cache.reset_metrics()
        if self._property_cache:
            self._property_cache.reset_metrics()

    # Type Enum Generation (Task 3.4)

    def generate_enums(self) -> Dict[str, Dict[str, Type[Enum]]]:
        """
        Generate type enums from schema

        Creates Python Enum classes for all entity types and relation types
        defined in the schema. The generated enums are string-based for
        backward compatibility with existing code.

        Returns:
            Dictionary with "entity_types" and "relation_types" keys,
            each containing a dictionary mapping type names to enum classes

        Example:
            >>> enums = schema_manager.generate_enums()
            >>> PersonEnum = enums["entity_types"]["Person"]
            >>> PersonEnum.PERSON  # "Person"
            >>>
            >>> WorksForEnum = enums["relation_types"]["WORKS_FOR"]
            >>> WorksForEnum.WORKS_FOR  # "WORKS_FOR"

        Note:
            The generated enums are backward compatible with string literals:
            >>> str(PersonEnum.PERSON) == "Person"  # True
            >>> PersonEnum.PERSON == "Person"  # True
        """
        generator = TypeEnumGenerator(self.schema)
        return generator.generate_all_enums()

    def __str__(self) -> str:
        cache_info = ""
        if self._enable_cache and self._entity_type_cache:
            stats = self.get_cache_stats()
            entity_hit_rate = stats["entity_types"].get("hit_rate", 0)
            cache_info = f", cache_hit_rate={entity_hit_rate:.2%}"
        return f"SchemaManager({self.schema}{cache_info})"

    def __repr__(self) -> str:
        return self.__str__()
