"""
Schema Manager

Service for managing knowledge graph schemas with CRUD operations.
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
        Initialize schema manager

        Args:
            schema: Initial schema (default: empty schema)
            cache_size: Maximum cache size (default: 1000)
            ttl_seconds: Cache TTL in seconds (default: 3600, None = no expiration)
            enable_cache: Whether to enable caching (default: True)
        """
        self.schema = schema if schema is not None else GraphSchema()
        self._transaction_schema: Optional[GraphSchema] = None

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

    # Entity Type Operations

    def create_entity_type(self, entity_type: EntityType) -> None:
        """
        Create a new entity type

        Args:
            entity_type: Entity type to create

        Raises:
            ValueError: If entity type already exists
        """
        self.schema.add_entity_type(entity_type)

        # Cache the new entity type
        if self._enable_cache and self._entity_type_cache:
            self._entity_type_cache.set(entity_type.name, entity_type)

    def update_entity_type(self, entity_type: EntityType) -> None:
        """
        Update an existing entity type

        Args:
            entity_type: Updated entity type

        Raises:
            ValueError: If entity type doesn't exist
        """
        self.schema.update_entity_type(entity_type)

        # Invalidate cache for this entity type
        if self._enable_cache and self._entity_type_cache:
            self._entity_type_cache.delete(entity_type.name)

    def delete_entity_type(self, type_name: str) -> None:
        """
        Delete an entity type

        Args:
            type_name: Name of entity type to delete

        Raises:
            ValueError: If entity type doesn't exist or is in use
        """
        self.schema.delete_entity_type(type_name)

        # Invalidate cache for this entity type
        if self._enable_cache and self._entity_type_cache:
            self._entity_type_cache.delete(type_name)

    def get_entity_type(self, type_name: str) -> Optional[EntityType]:
        """
        Get an entity type by name (with caching)

        Args:
            type_name: Name of entity type

        Returns:
            Entity type or None if not found
        """
        # Try cache first
        if self._enable_cache and self._entity_type_cache:
            cached = self._entity_type_cache.get(type_name)
            if cached is not None:
                return cached

        # Load from schema
        entity_type = self.schema.get_entity_type(type_name)

        # Cache the result if found
        if entity_type is not None and self._enable_cache and self._entity_type_cache:
            self._entity_type_cache.set(type_name, entity_type)

        return entity_type

    def list_entity_types(self) -> List[str]:
        """
        List all entity type names

        Returns:
            List of entity type names
        """
        return self.schema.get_entity_type_names()

    # Relation Type Operations

    def create_relation_type(self, relation_type: RelationType) -> None:
        """
        Create a new relation type

        Args:
            relation_type: Relation type to create

        Raises:
            ValueError: If relation type already exists
        """
        self.schema.add_relation_type(relation_type)

        # Cache the new relation type
        if self._enable_cache and self._relation_type_cache:
            self._relation_type_cache.set(relation_type.name, relation_type)

    def update_relation_type(self, relation_type: RelationType) -> None:
        """
        Update an existing relation type

        Args:
            relation_type: Updated relation type

        Raises:
            ValueError: If relation type doesn't exist
        """
        self.schema.update_relation_type(relation_type)

        # Invalidate cache for this relation type
        if self._enable_cache and self._relation_type_cache:
            self._relation_type_cache.delete(relation_type.name)

    def delete_relation_type(self, type_name: str) -> None:
        """
        Delete a relation type

        Args:
            type_name: Name of relation type to delete

        Raises:
            ValueError: If relation type doesn't exist
        """
        self.schema.delete_relation_type(type_name)

        # Invalidate cache for this relation type
        if self._enable_cache and self._relation_type_cache:
            self._relation_type_cache.delete(type_name)

    def get_relation_type(self, type_name: str) -> Optional[RelationType]:
        """
        Get a relation type by name (with caching)

        Args:
            type_name: Name of relation type

        Returns:
            Relation type or None if not found
        """
        # Try cache first
        if self._enable_cache and self._relation_type_cache:
            cached = self._relation_type_cache.get(type_name)
            if cached is not None:
                return cached

        # Load from schema
        relation_type = self.schema.get_relation_type(type_name)

        # Cache the result if found
        if relation_type is not None and self._enable_cache and self._relation_type_cache:
            self._relation_type_cache.set(type_name, relation_type)

        return relation_type

    def list_relation_types(self) -> List[str]:
        """
        List all relation type names

        Returns:
            List of relation type names
        """
        return self.schema.get_relation_type_names()

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

    def invalidate_cache(self, type_name: Optional[str] = None) -> None:
        """
        Invalidate cache entries

        Args:
            type_name: Specific type to invalidate (None = invalidate all)
        """
        if not self._enable_cache:
            return

        if type_name is None:
            # Clear all caches
            if self._entity_type_cache:
                self._entity_type_cache.clear()
            if self._relation_type_cache:
                self._relation_type_cache.clear()
            if self._property_cache:
                self._property_cache.clear()
        else:
            # Invalidate specific type
            if self._entity_type_cache:
                self._entity_type_cache.delete(type_name)
            if self._relation_type_cache:
                self._relation_type_cache.delete(type_name)

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
