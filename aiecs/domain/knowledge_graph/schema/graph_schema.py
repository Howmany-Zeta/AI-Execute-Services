"""
Graph Schema Container

Container for all entity types and relation types in the knowledge graph.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from aiecs.domain.knowledge_graph.schema.entity_type import EntityType
from aiecs.domain.knowledge_graph.schema.relation_type import RelationType


class GraphSchema(BaseModel):
    """
    Knowledge Graph Schema

    Container for all entity types and relation types in the knowledge graph.
    Provides methods for schema management and validation.

    Attributes:
        version: Schema version identifier
        entity_types: Dictionary of entity type schemas
        relation_types: Dictionary of relation type schemas
        description: Human-readable description of the schema

    Example:
        ```python
        schema = GraphSchema(
            version="1.0",
            description="Company knowledge graph schema"
        )
        schema.add_entity_type(person_type)
        schema.add_entity_type(company_type)
        schema.add_relation_type(works_for_type)
        ```
    """

    version: str = Field(default="1.0", description="Schema version identifier")

    entity_types: Dict[str, EntityType] = Field(
        default_factory=dict,
        description="Dictionary of entity type schemas (key=type name)",
    )

    relation_types: Dict[str, RelationType] = Field(
        default_factory=dict,
        description="Dictionary of relation type schemas (key=type name)",
    )

    description: Optional[str] = Field(default=None, description="Human-readable description of this schema")

    class Config:
        arbitrary_types_allowed = True

    # Entity Type Management

    def add_entity_type(self, entity_type: EntityType) -> None:
        """
        Add an entity type to the schema

        Args:
            entity_type: Entity type to add

        Raises:
            ValueError: If entity type already exists
        """
        if entity_type.name in self.entity_types:
            raise ValueError(f"Entity type '{entity_type.name}' already exists in schema")
        self.entity_types[entity_type.name] = entity_type

    def update_entity_type(self, entity_type: EntityType) -> None:
        """
        Update an existing entity type

        Args:
            entity_type: Updated entity type

        Raises:
            ValueError: If entity type doesn't exist
        """
        if entity_type.name not in self.entity_types:
            raise ValueError(f"Entity type '{entity_type.name}' not found in schema")
        self.entity_types[entity_type.name] = entity_type

    def delete_entity_type(self, type_name: str) -> None:
        """
        Delete an entity type from the schema

        Args:
            type_name: Name of entity type to delete

        Raises:
            ValueError: If entity type doesn't exist or is in use
        """
        if type_name not in self.entity_types:
            raise ValueError(f"Entity type '{type_name}' not found in schema")

        # Check if any relation types reference this entity type
        for rel_type in self.relation_types.values():
            if rel_type.source_entity_types and type_name in rel_type.source_entity_types:
                raise ValueError(f"Cannot delete entity type '{type_name}': " f"referenced by relation '{rel_type.name}' as source")
            if rel_type.target_entity_types and type_name in rel_type.target_entity_types:
                raise ValueError(f"Cannot delete entity type '{type_name}': " f"referenced by relation '{rel_type.name}' as target")

        del self.entity_types[type_name]

    def get_entity_type(self, type_name: str) -> Optional[EntityType]:
        """
        Get an entity type by name

        Args:
            type_name: Name of entity type

        Returns:
            Entity type or None if not found
        """
        return self.entity_types.get(type_name)

    def has_entity_type(self, type_name: str) -> bool:
        """
        Check if entity type exists

        Args:
            type_name: Name of entity type

        Returns:
            True if entity type exists
        """
        return type_name in self.entity_types

    # Relation Type Management

    def add_relation_type(self, relation_type: RelationType) -> None:
        """
        Add a relation type to the schema

        Args:
            relation_type: Relation type to add

        Raises:
            ValueError: If relation type already exists
        """
        if relation_type.name in self.relation_types:
            raise ValueError(f"Relation type '{relation_type.name}' already exists in schema")
        self.relation_types[relation_type.name] = relation_type

    def update_relation_type(self, relation_type: RelationType) -> None:
        """
        Update an existing relation type

        Args:
            relation_type: Updated relation type

        Raises:
            ValueError: If relation type doesn't exist
        """
        if relation_type.name not in self.relation_types:
            raise ValueError(f"Relation type '{relation_type.name}' not found in schema")
        self.relation_types[relation_type.name] = relation_type

    def delete_relation_type(self, type_name: str) -> None:
        """
        Delete a relation type from the schema

        Args:
            type_name: Name of relation type to delete

        Raises:
            ValueError: If relation type doesn't exist
        """
        if type_name not in self.relation_types:
            raise ValueError(f"Relation type '{type_name}' not found in schema")
        del self.relation_types[type_name]

    def get_relation_type(self, type_name: str) -> Optional[RelationType]:
        """
        Get a relation type by name

        Args:
            type_name: Name of relation type

        Returns:
            Relation type or None if not found
        """
        return self.relation_types.get(type_name)

    def has_relation_type(self, type_name: str) -> bool:
        """
        Check if relation type exists

        Args:
            type_name: Name of relation type

        Returns:
            True if relation type exists
        """
        return type_name in self.relation_types

    # Schema Queries

    def get_entity_type_names(self) -> List[str]:
        """Get list of all entity type names"""
        return list(self.entity_types.keys())

    def get_relation_type_names(self) -> List[str]:
        """Get list of all relation type names"""
        return list(self.relation_types.keys())

    def get_entity_types_with_property(self, property_name: str) -> List[EntityType]:
        """
        Get all entity types that have a specific property

        Args:
            property_name: Name of property to search for

        Returns:
            List of entity types with that property
        """
        return [entity_type for entity_type in self.entity_types.values() if property_name in entity_type.properties]

    def get_relation_types_for_entities(self, source_type: str, target_type: str) -> List[RelationType]:
        """
        Get all relation types allowed between two entity types

        Args:
            source_type: Source entity type name
            target_type: Target entity type name

        Returns:
            List of allowed relation types
        """
        allowed_relations = []

        for rel_type in self.relation_types.values():
            # Check if source type is allowed
            if rel_type.source_entity_types is not None:
                if source_type not in rel_type.source_entity_types:
                    continue

            # Check if target type is allowed
            if rel_type.target_entity_types is not None:
                if target_type not in rel_type.target_entity_types:
                    continue

            allowed_relations.append(rel_type)

        return allowed_relations

    def __str__(self) -> str:
        return f"GraphSchema(version='{self.version}', " f"entity_types={len(self.entity_types)}, " f"relation_types={len(self.relation_types)})"

    def __repr__(self) -> str:
        return self.__str__()
