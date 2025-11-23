"""
Relation Type Schema Definition

Defines the schema for relation types in the knowledge graph.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from aiecs.domain.knowledge_graph.schema.property_schema import PropertySchema


class RelationType(BaseModel):
    """
    Relation Type Schema

    Defines the schema for a type of relation in the knowledge graph,
    including source/target constraints and properties.

    Attributes:
        name: Relation type name (e.g., "WORKS_FOR", "KNOWS")
        description: Human-readable description
        properties: Dictionary of property schemas
        source_entity_types: Allowed source entity types (None = any)
        target_entity_types: Allowed target entity types (None = any)
        is_symmetric: Whether the relation is symmetric (A->B implies B->A)
        is_transitive: Whether the relation is transitive (A->B, B->C implies A->C)

    Example:
        ```python
        works_for = RelationType(
            name="WORKS_FOR",
            description="Employment relationship",
            source_entity_types=["Person"],
            target_entity_types=["Company"],
            properties={
                "since": PropertySchema(name="since", property_type=PropertyType.DATE),
                "role": PropertySchema(name="role", property_type=PropertyType.STRING),
            }
        )
        ```
    """

    name: str = Field(..., description="Relation type name (must be unique)")

    description: Optional[str] = Field(
        default=None,
        description="Human-readable description of this relation type",
    )

    properties: Dict[str, PropertySchema] = Field(
        default_factory=dict,
        description="Dictionary of property schemas (key=property name)",
    )

    source_entity_types: Optional[List[str]] = Field(
        default=None,
        description="Allowed source entity types (None = any type allowed)",
    )

    target_entity_types: Optional[List[str]] = Field(
        default=None,
        description="Allowed target entity types (None = any type allowed)",
    )

    is_symmetric: bool = Field(
        default=False,
        description="Whether relation is symmetric (A->B implies B->A)",
    )

    is_transitive: bool = Field(
        default=False,
        description="Whether relation is transitive (A->B, B->C implies A->C)",
    )

    class Config:
        arbitrary_types_allowed = True

    def add_property(self, prop: PropertySchema) -> None:
        """
        Add a property to this relation type

        Args:
            prop: Property schema to add
        """
        self.properties[prop.name] = prop

    def remove_property(self, property_name: str) -> None:
        """
        Remove a property from this relation type

        Args:
            property_name: Name of property to remove
        """
        if property_name in self.properties:
            del self.properties[property_name]

    def get_property(self, property_name: str) -> Optional[PropertySchema]:
        """
        Get a property schema by name

        Args:
            property_name: Name of property to get

        Returns:
            Property schema or None if not found
        """
        return self.properties.get(property_name)

    def validate_properties(self, properties: Dict[str, Any]) -> bool:
        """
        Validate a dictionary of properties against this schema

        Args:
            properties: Dictionary of properties to validate

        Returns:
            True if all properties are valid

        Raises:
            ValueError: If validation fails
        """
        # Check required properties
        for prop_name, prop_schema in self.properties.items():
            if prop_schema.required and prop_name not in properties:
                raise ValueError(f"Required property '{prop_name}' missing for relation type '{self.name}'")

        # Validate each provided property
        for prop_name, prop_value in properties.items():
            if prop_name in self.properties:
                prop_schema = self.properties[prop_name]
                prop_schema.validate_value(prop_value)

        return True

    def validate_entity_types(self, source_entity_type: str, target_entity_type: str) -> bool:
        """
        Validate that source and target entity types are allowed

        Args:
            source_entity_type: Source entity type name
            target_entity_type: Target entity type name

        Returns:
            True if entity types are valid

        Raises:
            ValueError: If entity types are not allowed
        """
        if self.source_entity_types is not None:
            if source_entity_type not in self.source_entity_types:
                raise ValueError(f"Source entity type '{source_entity_type}' not allowed for " f"relation '{self.name}'. Allowed: {self.source_entity_types}")

        if self.target_entity_types is not None:
            if target_entity_type not in self.target_entity_types:
                raise ValueError(f"Target entity type '{target_entity_type}' not allowed for " f"relation '{self.name}'. Allowed: {self.target_entity_types}")

        return True

    def __str__(self) -> str:
        return f"RelationType(name='{self.name}', properties={len(self.properties)})"

    def __repr__(self) -> str:
        return self.__str__()
