"""
Entity Type Schema Definition

Defines the schema for entity types in the knowledge graph.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from aiecs.domain.knowledge_graph.schema.property_schema import PropertySchema


class EntityType(BaseModel):
    """
    Entity Type Schema

    Defines the schema for a type of entity in the knowledge graph,
    including its properties and constraints.

    Attributes:
        name: Entity type name (e.g., "Person", "Company")
        description: Human-readable description
        properties: Dictionary of property schemas
        parent_type: Optional parent entity type for inheritance
        is_abstract: Whether this is an abstract type (cannot be instantiated)

    Example:
        ```python
        person_type = EntityType(
            name="Person",
            description="A person entity",
            properties={
                "name": PropertySchema(name="name", property_type=PropertyType.STRING, required=True),
                "age": PropertySchema(name="age", property_type=PropertyType.INTEGER),
            }
        )
        ```
    """

    name: str = Field(..., description="Entity type name (must be unique)")

    description: Optional[str] = Field(
        default=None,
        description="Human-readable description of this entity type",
    )

    properties: Dict[str, PropertySchema] = Field(
        default_factory=dict,
        description="Dictionary of property schemas (key=property name)",
    )

    parent_type: Optional[str] = Field(default=None, description="Parent entity type name for inheritance")

    is_abstract: bool = Field(
        default=False,
        description="Whether this is an abstract type (cannot be instantiated)",
    )

    class Config:
        arbitrary_types_allowed = True

    def add_property(self, prop: PropertySchema) -> None:
        """
        Add a property to this entity type

        Args:
            prop: Property schema to add
        """
        self.properties[prop.name] = prop

    def remove_property(self, property_name: str) -> None:
        """
        Remove a property from this entity type

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
                raise ValueError(f"Required property '{prop_name}' missing for entity type '{self.name}'")

        # Validate each provided property
        for prop_name, prop_value in properties.items():
            if prop_name in self.properties:
                prop_schema = self.properties[prop_name]
                prop_schema.validate_value(prop_value)

        return True

    def get_required_properties(self) -> List[str]:
        """
        Get list of required property names

        Returns:
            List of required property names
        """
        return [prop.name for prop in self.properties.values() if prop.required]

    def __str__(self) -> str:
        return f"EntityType(name='{self.name}', properties={len(self.properties)})"

    def __repr__(self) -> str:
        return self.__str__()
