"""
Schema Manager

Service for managing knowledge graph schemas with CRUD operations.
"""

from typing import Optional, List
import json
from pathlib import Path
from aiecs.domain.knowledge_graph.schema.graph_schema import GraphSchema
from aiecs.domain.knowledge_graph.schema.entity_type import EntityType
from aiecs.domain.knowledge_graph.schema.relation_type import RelationType
from aiecs.domain.knowledge_graph.schema.property_schema import PropertySchema


class SchemaManager:
    """
    Schema Manager Service

    Manages knowledge graph schemas with support for:
    - Creating, reading, updating, deleting entity and relation types
    - Schema persistence (save/load from JSON)
    - Schema validation
    - Transaction-like operations (commit/rollback)

    Example:
        ```python
        manager = SchemaManager()

        # Add entity type
        person_type = EntityType(name="Person", ...)
        manager.create_entity_type(person_type)

        # Save schema
        manager.save("./schema.json")
        ```
    """

    def __init__(self, schema: Optional[GraphSchema] = None):
        """
        Initialize schema manager

        Args:
            schema: Initial schema (default: empty schema)
        """
        self.schema = schema if schema is not None else GraphSchema()
        self._transaction_schema: Optional[GraphSchema] = None

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

    def update_entity_type(self, entity_type: EntityType) -> None:
        """
        Update an existing entity type

        Args:
            entity_type: Updated entity type

        Raises:
            ValueError: If entity type doesn't exist
        """
        self.schema.update_entity_type(entity_type)

    def delete_entity_type(self, type_name: str) -> None:
        """
        Delete an entity type

        Args:
            type_name: Name of entity type to delete

        Raises:
            ValueError: If entity type doesn't exist or is in use
        """
        self.schema.delete_entity_type(type_name)

    def get_entity_type(self, type_name: str) -> Optional[EntityType]:
        """
        Get an entity type by name

        Args:
            type_name: Name of entity type

        Returns:
            Entity type or None if not found
        """
        return self.schema.get_entity_type(type_name)

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

    def update_relation_type(self, relation_type: RelationType) -> None:
        """
        Update an existing relation type

        Args:
            relation_type: Updated relation type

        Raises:
            ValueError: If relation type doesn't exist
        """
        self.schema.update_relation_type(relation_type)

    def delete_relation_type(self, type_name: str) -> None:
        """
        Delete a relation type

        Args:
            type_name: Name of relation type to delete

        Raises:
            ValueError: If relation type doesn't exist
        """
        self.schema.delete_relation_type(type_name)

    def get_relation_type(self, type_name: str) -> Optional[RelationType]:
        """
        Get a relation type by name

        Args:
            type_name: Name of relation type

        Returns:
            Relation type or None if not found
        """
        return self.schema.get_relation_type(type_name)

    def list_relation_types(self) -> List[str]:
        """
        List all relation type names

        Returns:
            List of relation type names
        """
        return self.schema.get_relation_type_names()

    # Schema Validation

    def validate_entity(
        self,
        entity_type_name: str,
        properties: dict
    ) -> bool:
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
        properties: dict
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
        schema_dict = self.schema.model_dump(mode='json')

        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
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
        with open(file_path, 'r', encoding='utf-8') as f:
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

    def __str__(self) -> str:
        return f"SchemaManager({self.schema})"

    def __repr__(self) -> str:
        return self.__str__()

