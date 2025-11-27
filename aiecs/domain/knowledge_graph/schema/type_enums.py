"""
Type Enums

Dynamic enum generation for entity and relation types from schema.

Phase: 3.4 - Type Enums
Version: 1.0
"""

from enum import Enum
from typing import Type, Dict
from aiecs.domain.knowledge_graph.schema.graph_schema import GraphSchema


class EntityTypeEnum(str, Enum):
    """
    Base class for entity type enums

    Dynamically generated enums inherit from this class.
    Enums are string-based for backward compatibility.

    Example:
        >>> PersonType = EntityTypeEnum("PersonType", {"PERSON": "Person"})
        >>> PersonType.PERSON
        'Person'
        >>> str(PersonType.PERSON)
        'Person'
    """

    def __str__(self) -> str:
        """Return the enum value (for backward compatibility)"""
        return self.value

    def __repr__(self) -> str:
        """Return the enum representation"""
        return f"{self.__class__.__name__}.{self.name}"


class RelationTypeEnum(str, Enum):
    """
    Base class for relation type enums

    Dynamically generated enums inherit from this class.
    Enums are string-based for backward compatibility.

    Example:
        >>> WorksForType = RelationTypeEnum("WorksForType", {"WORKS_FOR": "WORKS_FOR"})
        >>> WorksForType.WORKS_FOR
        'WORKS_FOR'
        >>> str(WorksForType.WORKS_FOR)
        'WORKS_FOR'
    """

    def __str__(self) -> str:
        """Return the enum value (for backward compatibility)"""
        return self.value

    def __repr__(self) -> str:
        """Return the enum representation"""
        return f"{self.__class__.__name__}.{self.name}"


class TypeEnumGenerator:
    """
    Utility for generating type enums from schema

    Generates Python Enum classes for entity types and relation types
    defined in a GraphSchema. The generated enums are string-based for
    backward compatibility with existing code that uses string literals.

    Example:
        >>> generator = TypeEnumGenerator(schema)
        >>> entity_enums = generator.generate_entity_type_enums()
        >>> relation_enums = generator.generate_relation_type_enums()
        >>>
        >>> # Use generated enums
        >>> PersonType = entity_enums["Person"]
        >>> person_type = PersonType.PERSON  # "Person"
    """

    def __init__(self, schema: GraphSchema):
        """
        Initialize enum generator

        Args:
            schema: Graph schema to generate enums from
        """
        self.schema = schema

    def generate_entity_type_enums(self) -> Dict[str, Type[EntityTypeEnum]]:
        """
        Generate entity type enums from schema

        Creates an enum class for each entity type in the schema.
        The enum name is the entity type name, and the enum value
        is also the entity type name (for backward compatibility).

        Returns:
            Dictionary mapping entity type names to enum classes

        Example:
            >>> enums = generator.generate_entity_type_enums()
            >>> PersonEnum = enums["Person"]
            >>> PersonEnum.PERSON  # "Person"
        """
        enums = {}

        for entity_type_name in self.schema.get_entity_type_names():
            # Create enum name (convert to uppercase with underscores)
            enum_member_name = self._to_enum_name(entity_type_name)

            # Create enum class dynamically using type()
            enum_class = type(
                entity_type_name + "Enum",
                (EntityTypeEnum,),
                {enum_member_name: entity_type_name}
            )

            enums[entity_type_name] = enum_class

        return enums

    def generate_relation_type_enums(
        self,
    ) -> Dict[str, Type[RelationTypeEnum]]:
        """
        Generate relation type enums from schema

        Creates an enum class for each relation type in the schema.
        The enum name is the relation type name, and the enum value
        is also the relation type name (for backward compatibility).

        Returns:
            Dictionary mapping relation type names to enum classes

        Example:
            >>> enums = generator.generate_relation_type_enums()
            >>> WorksForEnum = enums["WORKS_FOR"]
            >>> WorksForEnum.WORKS_FOR  # "WORKS_FOR"
        """
        enums = {}

        for relation_type_name in self.schema.get_relation_type_names():
            # Create enum name (convert to uppercase with underscores)
            enum_member_name = self._to_enum_name(relation_type_name)

            # Create enum class dynamically using type()
            enum_class = type(
                relation_type_name + "Enum",
                (RelationTypeEnum,),
                {enum_member_name: relation_type_name}
            )

            enums[relation_type_name] = enum_class

        return enums

    def generate_all_enums(self) -> Dict[str, Dict[str, Type[Enum]]]:
        """
        Generate all type enums from schema

        Returns:
            Dictionary with "entity_types" and "relation_types" keys,
            each containing a dictionary of enum classes

        Example:
            >>> enums = generator.generate_all_enums()
            >>> PersonEnum = enums["entity_types"]["Person"]
            >>> WorksForEnum = enums["relation_types"]["WORKS_FOR"]
        """
        from typing import cast
        return {
            "entity_types": cast(Dict[str, Type[Enum]], self.generate_entity_type_enums()),
            "relation_types": cast(Dict[str, Type[Enum]], self.generate_relation_type_enums()),
        }

    @staticmethod
    def _to_enum_name(type_name: str) -> str:
        """
        Convert type name to enum member name

        Converts CamelCase or snake_case to UPPER_CASE.

        Args:
            type_name: Type name to convert

        Returns:
            Enum member name in UPPER_CASE

        Example:
            >>> TypeEnumGenerator._to_enum_name("Person")
            'PERSON'
            >>> TypeEnumGenerator._to_enum_name("WorksFor")
            'WORKS_FOR'
            >>> TypeEnumGenerator._to_enum_name("WORKS_FOR")
            'WORKS_FOR'
        """
        # If already uppercase, return as-is
        if type_name.isupper():
            return type_name

        # Convert CamelCase to UPPER_CASE
        result = []
        for i, char in enumerate(type_name):
            if char.isupper() and i > 0 and type_name[i - 1].islower():
                result.append("_")
            result.append(char.upper())

        return "".join(result)
