"""
Property Schema Definition

Defines the schema for properties that can be attached to entities and relations.
"""

from typing import Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class PropertyType(str, Enum):
    """Property data types"""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    LIST = "list"
    DICT = "dict"
    ANY = "any"


class PropertySchema(BaseModel):
    """
    Property Schema Definition

    Defines the schema for a single property that can be attached to
    entities or relations in the knowledge graph.

    Attributes:
        name: Property name
        property_type: Data type of the property
        required: Whether the property is required
        description: Human-readable description
        default: Default value if not provided
        allowed_values: List of allowed values (for enums)
        min_value: Minimum value (for numeric types)
        max_value: Maximum value (for numeric types)

    Example:
        ```python
        prop = PropertySchema(
            name="age",
            property_type=PropertyType.INTEGER,
            required=False,
            description="Person's age in years",
            min_value=0,
            max_value=150
        )
        ```
    """

    name: str = Field(
        ...,
        description="Property name (must be unique within entity/relation type)",
    )

    property_type: PropertyType = Field(default=PropertyType.STRING, description="Data type of the property")

    required: bool = Field(default=False, description="Whether this property is required")

    description: Optional[str] = Field(default=None, description="Human-readable description of the property")

    default: Optional[Any] = Field(default=None, description="Default value if property is not provided")

    allowed_values: Optional[List[Any]] = Field(
        default=None,
        description="List of allowed values (for enum-like properties)",
    )

    min_value: Optional[float] = Field(default=None, description="Minimum value (for numeric types)")

    max_value: Optional[float] = Field(default=None, description="Maximum value (for numeric types)")

    class Config:
        use_enum_values = True

    def validate_value(self, value: Any) -> bool:
        """
        Validate a value against this schema

        Args:
            value: Value to validate

        Returns:
            True if value is valid

        Raises:
            ValueError: If value doesn't match schema
        """
        if value is None:
            if self.required:
                raise ValueError(f"Property '{self.name}' is required but got None")
            return True

        # Type validation
        if self.property_type == PropertyType.STRING:
            if not isinstance(value, str):
                raise ValueError(f"Property '{self.name}' must be string, got {type(value)}")

        elif self.property_type == PropertyType.INTEGER:
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"Property '{self.name}' must be integer, got {type(value)}")

        elif self.property_type == PropertyType.FLOAT:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"Property '{self.name}' must be numeric, got {type(value)}")

        elif self.property_type == PropertyType.BOOLEAN:
            if not isinstance(value, bool):
                raise ValueError(f"Property '{self.name}' must be boolean, got {type(value)}")

        elif self.property_type == PropertyType.LIST:
            if not isinstance(value, list):
                raise ValueError(f"Property '{self.name}' must be list, got {type(value)}")

        elif self.property_type == PropertyType.DICT:
            if not isinstance(value, dict):
                raise ValueError(f"Property '{self.name}' must be dict, got {type(value)}")

        # Allowed values validation
        if self.allowed_values is not None:
            if value not in self.allowed_values:
                raise ValueError(f"Property '{self.name}' value must be one of {self.allowed_values}, got {value}")

        # Range validation for numeric types
        if self.property_type in (PropertyType.INTEGER, PropertyType.FLOAT):
            if self.min_value is not None and value < self.min_value:
                raise ValueError(f"Property '{self.name}' must be >= {self.min_value}, got {value}")
            if self.max_value is not None and value > self.max_value:
                raise ValueError(f"Property '{self.name}' must be <= {self.max_value}, got {value}")

        return True

    def __str__(self) -> str:
        required_str = " (required)" if self.required else ""
        return f"PropertySchema(name='{self.name}', type={self.property_type}{required_str})"

    def __repr__(self) -> str:
        return self.__str__()
