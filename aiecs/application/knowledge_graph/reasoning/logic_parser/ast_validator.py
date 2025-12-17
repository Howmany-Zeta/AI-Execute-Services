"""
AST Validator for Logic Query Parser

This module provides comprehensive validation of AST nodes against the knowledge graph schema.
It validates entity types, properties, relation types, property types, and variable references.

Design Principles:
1. Schema-aware validation (entity types, properties, relations)
2. Error accumulation (collect all errors, don't stop at first)
3. Helpful error messages with suggestions
4. Type checking (property values match expected types)

Phase: 2.4 - Logic Query Parser
Task: 3.1 - Implement AST Validator
Version: 1.0
"""

from typing import Any, List, Optional, Set
from .ast_nodes import (
    ValidationError,
    ASTNode,
    QueryNode,
    FindNode,
    TraversalNode,
    PropertyFilterNode,
    BooleanFilterNode,
)


class ASTValidator:
    """
    AST Validator with schema integration

    This class provides comprehensive validation of AST nodes against the
    knowledge graph schema. It validates:
    - Entity types exist in schema
    - Properties exist in entity schema
    - Relation types exist in schema
    - Property values match expected types
    - Relation endpoints match entity types
    - Variable references are defined before use

    The validator accumulates all errors instead of stopping at the first error.

    Example:
        ```python
        from aiecs.domain.knowledge_graph.schema import SchemaManager

        schema = SchemaManager.load("schema.json")
        validator = ASTValidator(schema)

        errors = validator.validate(ast_node)
        if errors:
            for error in errors:
                print(f"Line {error.line}: {error.message}")
        ```
    """

    def __init__(self, schema: Any):
        """
        Initialize AST validator

        Args:
            schema: SchemaManager instance for validation
        """
        self.schema = schema
        self.current_entity_type: Optional[str] = None
        self.defined_variables: Set[str] = set()

    # ========================================================================
    # Main Validation Entry Point
    # ========================================================================

    def validate(self, node: ASTNode) -> List[ValidationError]:
        """
        Validate an AST node and all its children

        This is the main entry point for validation. It accumulates all
        errors from the node and its children.

        Args:
            node: AST node to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Dispatch to specific validation method based on node type
        if isinstance(node, QueryNode):
            errors.extend(self.validate_query_node(node))
        elif isinstance(node, FindNode):
            errors.extend(self.validate_find_node(node))
        elif isinstance(node, TraversalNode):
            errors.extend(self.validate_traversal_node(node))
        elif isinstance(node, PropertyFilterNode):
            errors.extend(self.validate_property_filter_node(node))
        elif isinstance(node, BooleanFilterNode):
            errors.extend(self.validate_boolean_filter_node(node))
        else:
            # Fallback to node's own validate method
            errors.extend(node.validate(self.schema))

        return errors

    # ========================================================================
    # Node-Specific Validation Methods
    # ========================================================================

    def validate_query_node(self, node: QueryNode) -> List[ValidationError]:
        """
        Validate QueryNode

        Validates:
        - FindNode
        - All TraversalNodes
        - Entity type consistency across traversals

        Args:
            node: QueryNode to validate

        Returns:
            List of validation errors
        """
        errors: List[ValidationError] = []

        # Validate FindNode
        errors.extend(self.validate_find_node(node.find))

        # Track current entity type for traversal validation
        self.current_entity_type = node.find.entity_type

        # Validate all traversals
        for traversal in node.traversals:
            errors.extend(self.validate_traversal_node(traversal))

        return errors

    def validate_find_node(self, node: FindNode) -> List[ValidationError]:
        """
        Validate FindNode

        Validates:
        - Entity type exists in schema
        - All filters reference valid properties

        Args:
            node: FindNode to validate

        Returns:
            List of validation errors
        """
        errors: List[ValidationError] = []

        # Validate entity type exists
        errors.extend(self.validate_entity_type(node.entity_type, node.line, node.column))

        # Set current entity type for property validation
        self.current_entity_type = node.entity_type

        # Validate all filters
        for filter_node in node.filters:
            errors.extend(self.validate(filter_node))

        return errors

    def validate_traversal_node(self, node: TraversalNode) -> List[ValidationError]:
        """
        Validate TraversalNode

        Validates:
        - Relation type exists in schema
        - Relation endpoints match current entity type
        - Direction is valid

        Args:
            node: TraversalNode to validate

        Returns:
            List of validation errors
        """
        errors: List[ValidationError] = []

        # Validate relation type exists
        errors.extend(self.validate_relation_type(node.relation_type, node.line, node.column))

        # Validate relation endpoints if we have a current entity type
        if self.current_entity_type:
            errors.extend(
                self.validate_relation_endpoints(
                    node.relation_type,
                    self.current_entity_type,
                    node.direction or "outgoing",
                    node.line,
                    node.column,
                )
            )

        # Validate direction
        if node.direction and node.direction not in ["incoming", "outgoing"]:
            errors.append(
                ValidationError(
                    line=node.line,
                    column=node.column,
                    message=f"Invalid direction '{node.direction}'. Must be 'incoming' or 'outgoing'",
                    suggestion="Use 'INCOMING' or 'OUTGOING'",
                )
            )

        return errors

    def validate_property_filter_node(self, node: PropertyFilterNode) -> List[ValidationError]:
        """
        Validate PropertyFilterNode

        Validates:
        - Property exists in current entity type
        - Property value type matches schema
        - Operator is valid for property type

        Args:
            node: PropertyFilterNode to validate

        Returns:
            List of validation errors
        """
        errors: List[ValidationError] = []

        # Validate operator
        valid_operators = ["==", "!=", ">", "<", ">=", "<=", "IN", "CONTAINS"]
        if node.operator not in valid_operators:
            errors.append(
                ValidationError(
                    line=node.line,
                    column=node.column,
                    message=f"Invalid operator '{node.operator}'",
                    suggestion=f"Valid operators: {', '.join(valid_operators)}",
                )
            )

        # Validate property exists in current entity type
        if self.current_entity_type:
            errors.extend(
                self.validate_property(
                    self.current_entity_type,
                    node.property_path,
                    node.line,
                    node.column,
                )
            )

            # Validate property value type
            errors.extend(
                self.validate_property_value_type(
                    self.current_entity_type,
                    node.property_path,
                    node.value,
                    node.operator,
                    node.line,
                    node.column,
                )
            )

        # Validate operator-specific constraints
        if node.operator == "IN" and not isinstance(node.value, list):
            errors.append(
                ValidationError(
                    line=node.line,
                    column=node.column,
                    message=f"IN operator requires a list value, got {type(node.value).__name__}",
                    suggestion="Use a list like ['value1', 'value2']",
                )
            )

        if node.operator == "CONTAINS" and not isinstance(node.value, str):
            errors.append(
                ValidationError(
                    line=node.line,
                    column=node.column,
                    message=f"CONTAINS operator requires a string value, got {type(node.value).__name__}",
                    suggestion="Use a string value",
                )
            )

        return errors

    def validate_boolean_filter_node(self, node: BooleanFilterNode) -> List[ValidationError]:
        """
        Validate BooleanFilterNode

        Validates:
        - Operator is valid (AND, OR, NOT)
        - Has at least one operand
        - All operands are valid

        Args:
            node: BooleanFilterNode to validate

        Returns:
            List of validation errors
        """
        errors: List[ValidationError] = []

        # Validate operator
        valid_operators = ["AND", "OR", "NOT"]
        if node.operator not in valid_operators:
            errors.append(
                ValidationError(
                    line=node.line,
                    column=node.column,
                    message=f"Invalid boolean operator '{node.operator}'",
                    suggestion=f"Valid operators: {', '.join(valid_operators)}",
                )
            )

        # Validate operand count
        if not node.operands:
            errors.append(
                ValidationError(
                    line=node.line,
                    column=node.column,
                    message=f"Boolean operator '{node.operator}' requires at least one operand",
                )
            )

        # Validate all operands
        for operand in node.operands:
            errors.extend(self.validate(operand))

        return errors

    # ========================================================================
    # Helper Validation Methods
    # ========================================================================

    def validate_entity_type(self, entity_type: str, line: int, column: int) -> List[ValidationError]:
        """
        Validate that an entity type exists in the schema

        Args:
            entity_type: Entity type name to validate
            line: Line number for error reporting
            column: Column number for error reporting

        Returns:
            List of validation errors
        """
        errors: List[ValidationError] = []

        # Check if schema has the method
        if not hasattr(self.schema, "get_entity_type"):
            return errors

        # Check if entity type exists
        entity_schema = self.schema.get_entity_type(entity_type)
        if entity_schema is None:
            # Get available types for suggestion
            available_types = []
            if hasattr(self.schema, "list_entity_types"):
                available_types = self.schema.list_entity_types()

            suggestion = None
            if available_types:
                suggestion = f"Available entity types: {', '.join(available_types[:5])}"
                if len(available_types) > 5:
                    suggestion += f" (and {len(available_types) - 5} more)"

            errors.append(
                ValidationError(
                    line=line,
                    column=column,
                    message=f"Entity type '{entity_type}' not found in schema",
                    suggestion=suggestion,
                )
            )

        return errors

    def validate_relation_type(self, relation_type: str, line: int, column: int) -> List[ValidationError]:
        """
        Validate that a relation type exists in the schema

        Args:
            relation_type: Relation type name to validate
            line: Line number for error reporting
            column: Column number for error reporting

        Returns:
            List of validation errors
        """
        errors: List[ValidationError] = []

        # Check if schema has the method
        if not hasattr(self.schema, "get_relation_type"):
            return errors

        # Check if relation type exists
        relation_schema = self.schema.get_relation_type(relation_type)
        if relation_schema is None:
            # Get available types for suggestion
            available_types = []
            if hasattr(self.schema, "list_relation_types"):
                available_types = self.schema.list_relation_types()

            suggestion = None
            if available_types:
                suggestion = f"Available relation types: {', '.join(available_types[:5])}"
                if len(available_types) > 5:
                    suggestion += f" (and {len(available_types) - 5} more)"

            errors.append(
                ValidationError(
                    line=line,
                    column=column,
                    message=f"Relation type '{relation_type}' not found in schema",
                    suggestion=suggestion,
                )
            )

        return errors

    def validate_property(self, entity_type: str, property_path: str, line: int, column: int) -> List[ValidationError]:
        """
        Validate that a property exists in an entity type

        Supports nested property paths (e.g., "address.city") by recursively
        validating each part of the path.

        Args:
            entity_type: Entity type name
            property_path: Property path (may be nested like "address.city")
            line: Line number for error reporting
            column: Column number for error reporting

        Returns:
            List of validation errors
        """
        errors: List[ValidationError] = []

        # Get entity type schema
        if not hasattr(self.schema, "get_entity_type"):
            return errors

        entity_schema = self.schema.get_entity_type(entity_type)
        if entity_schema is None:
            return errors  # Entity type error already reported

        # Validate nested property path recursively
        errors.extend(
            self._validate_nested_property_path(
                entity_schema=entity_schema,
                property_path=property_path,
                entity_type=entity_type,
                line=line,
                column=column,
            )
        )

        return errors

    def _validate_nested_property_path(
        self,
        entity_schema: Any,
        property_path: str,
        entity_type: str,
        line: int,
        column: int,
        current_path: str = "",
    ) -> List[ValidationError]:
        """
        Recursively validate a nested property path

        Args:
            entity_schema: Current entity schema (may be nested)
            property_path: Remaining property path to validate
            entity_type: Root entity type name
            line: Line number for error reporting
            column: Column number for error reporting
            current_path: Accumulated path so far (for error messages)

        Returns:
            List of validation errors
        """
        errors: List[ValidationError] = []

        # Split property path into parts
        property_parts = property_path.split(".")
        current_property = property_parts[0]
        remaining_path = ".".join(property_parts[1:]) if len(property_parts) > 1 else None

        # Build full path for error messages
        full_path = f"{current_path}.{current_property}" if current_path else current_property

        # Check if entity schema has get_property method
        if not hasattr(entity_schema, "get_property"):
            return errors

        # Get property schema
        property_schema = entity_schema.get_property(current_property)
        if property_schema is None:
            # Property doesn't exist - get available properties for suggestion
            available_props = []
            if hasattr(entity_schema, "properties"):
                available_props = list(entity_schema.properties.keys())
            elif hasattr(entity_schema, "get_property_names"):
                available_props = entity_schema.get_property_names()

            suggestion = None
            if available_props:
                context = f"{entity_type}.{current_path}" if current_path else entity_type
                suggestion = f"Available properties for {context}: {', '.join(available_props[:5])}"
                if len(available_props) > 5:
                    suggestion += f" (and {len(available_props) - 5} more)"

            errors.append(
                ValidationError(
                    line=line,
                    column=column,
                    message=f"Property '{full_path}' not found in {entity_type if not current_path else current_path}",
                    suggestion=suggestion,
                )
            )
            return errors  # Can't continue validation if property doesn't exist

        # Check if there's more nesting to validate
        if remaining_path:
            # Check if current property is DICT type (supports nesting)
            if not hasattr(property_schema, "property_type"):
                # Can't determine if nesting is supported
                errors.append(
                    ValidationError(
                        line=line,
                        column=column,
                        message=f"Cannot validate nested path '{full_path}.{remaining_path}': "
                        f"property '{current_property}' type unknown",
                        suggestion="Ensure property schema defines property_type",
                    )
                )
                return errors

            property_type = property_schema.property_type

            # Check if property type supports nesting
            # DICT type supports nesting, but we need nested schema
            if hasattr(property_type, "value"):
                type_value = property_type.value
            elif hasattr(property_type, "name"):
                type_value = property_type.name
            else:
                type_value = str(property_type)

            # Import PropertyType to check if it's DICT
            from aiecs.domain.knowledge_graph.schema.property_schema import PropertyType

            if type_value == PropertyType.DICT.value or type_value == "dict":
                # Property is DICT type - check for nested schema
                nested_schema = self._get_nested_schema(property_schema)
                if nested_schema is None:
                    # No nested schema defined - can't validate deeper nesting
                    errors.append(
                        ValidationError(
                            line=line,
                            column=column,
                            message=f"Cannot validate nested path '{full_path}.{remaining_path}': "
                            f"property '{current_property}' is DICT type but nested schema not defined",
                            suggestion=f"Define nested schema for '{current_property}' or use flat property path",
                        )
                    )
                    return errors

                # Recursively validate remaining path
                errors.extend(
                    self._validate_nested_property_path(
                        entity_schema=nested_schema,
                        property_path=remaining_path,
                        entity_type=entity_type,
                        line=line,
                        column=column,
                        current_path=full_path,
                    )
                )
            else:
                # Property is not DICT type - can't nest further
                errors.append(
                    ValidationError(
                        line=line,
                        column=column,
                        message=f"Cannot access nested path '{full_path}.{remaining_path}': "
                        f"property '{current_property}' is {type_value} type, not DICT",
                        suggestion=f"Use '{full_path}' directly or change property type to DICT",
                    )
                )

        return errors

    def _get_nested_schema(self, property_schema: Any) -> Optional[Any]:
        """
        Get nested schema for a DICT property

        Checks for nested schema in multiple ways:
        1. property_schema.nested_schema attribute
        2. property_schema.schema attribute (if not a callable method)
        3. property_schema.properties attribute (treat as EntityType-like)

        Args:
            property_schema: Property schema to get nested schema from

        Returns:
            Nested schema object or None if not found
        """
        # Check for explicit nested_schema attribute
        if hasattr(property_schema, "nested_schema"):
            nested_schema = getattr(property_schema, "nested_schema", None)
            if nested_schema is not None:
                return nested_schema

        # Check for schema attribute (but not if it's a callable method)
        if hasattr(property_schema, "schema"):
            schema_attr = getattr(property_schema, "schema", None)
            # Only use if it's not callable (Pydantic models have schema() method)
            if schema_attr is not None and not callable(schema_attr):
                return schema_attr

        # Check if property_schema has properties attribute (treat as EntityType-like)
        if hasattr(property_schema, "properties"):
            properties = getattr(property_schema, "properties", None)
            # Only use if it's a dict-like structure (not a Pydantic method)
            if properties and isinstance(properties, dict) and len(properties) > 0:
                # Create a mock entity schema-like object
                class NestedSchema:
                    def __init__(self, properties):
                        self.properties = properties

                    def get_property(self, property_name: str):
                        if isinstance(self.properties, dict):
                            return self.properties.get(property_name)
                        return None

                    def get_property_names(self):
                        if isinstance(self.properties, dict):
                            return list(self.properties.keys())
                        return []

                return NestedSchema(properties)

        return None

    def validate_property_value_type(
        self,
        entity_type: str,
        property_path: str,
        value: Any,
        operator: str,
        line: int,
        column: int,
    ) -> List[ValidationError]:
        """
        Validate that a property value matches the expected type

        Supports nested property paths by recursively finding the final property schema.

        Args:
            entity_type: Entity type name
            property_path: Property path (may be nested like "address.city")
            value: Value to validate
            operator: Operator being used
            line: Line number for error reporting
            column: Column number for error reporting

        Returns:
            List of validation errors
        """
        errors: List[ValidationError] = []

        # Get entity type schema
        if not hasattr(self.schema, "get_entity_type"):
            return errors

        entity_schema = self.schema.get_entity_type(entity_type)
        if entity_schema is None:
            return errors

        # Get property schema for nested path
        property_schema = self._get_property_schema_for_path(entity_schema, property_path)
        if property_schema is None:
            return errors  # Property error already reported

        # Get property type
        if not hasattr(property_schema, "property_type"):
            return errors

        property_type = property_schema.property_type

        # Map property types to Python types
        type_map = {
            "STRING": str,
            "INTEGER": int,
            "FLOAT": float,
            "BOOLEAN": bool,
            "DATE": str,  # Dates are typically strings in queries
            "DATETIME": str,
        }

        # Get expected Python type
        expected_type = None
        if hasattr(property_type, "value"):
            # Enum type
            expected_type = type_map.get(property_type.value)
        elif hasattr(property_type, "name"):
            # String type name
            expected_type = type_map.get(property_type.name)
        elif isinstance(property_type, str):
            # Direct string type
            expected_type = type_map.get(property_type)

        if expected_type is None:
            return errors  # Unknown type, skip validation

        # For IN operator, check list elements
        if operator == "IN":
            if isinstance(value, list):
                for item in value:
                    if not isinstance(item, expected_type):
                        errors.append(
                            ValidationError(
                                line=line,
                                column=column,
                                message=f"Property '{property_path}' expects {expected_type.__name__} values, "
                                f"but list contains {type(item).__name__}",
                                suggestion=f"Ensure all list values are {expected_type.__name__}",
                            )
                        )
                        break  # Only report once
            return errors

        # Check value type
        if not isinstance(value, expected_type):
            errors.append(
                ValidationError(
                    line=line,
                    column=column,
                    message=f"Property '{property_path}' expects {expected_type.__name__} value, "
                    f"got {type(value).__name__}",
                    suggestion=f"Use a {expected_type.__name__} value",
                )
            )

        return errors

    def _get_property_schema_for_path(self, entity_schema: Any, property_path: str) -> Optional[Any]:
        """
        Get property schema for a nested property path

        Args:
            entity_schema: Entity schema to start from
            property_path: Property path (may be nested like "address.city")

        Returns:
            Property schema for the final property in the path, or None if not found
        """
        property_parts = property_path.split(".")
        current_schema = entity_schema

        for i, part in enumerate(property_parts):
            if not hasattr(current_schema, "get_property"):
                return None

            property_schema = current_schema.get_property(part)
            if property_schema is None:
                return None

            # If this is the last part, return the property schema
            if i == len(property_parts) - 1:
                return property_schema

            # Otherwise, check if this property supports nesting
            if not hasattr(property_schema, "property_type"):
                return None

            property_type = property_schema.property_type
            type_value = None
            if hasattr(property_type, "value"):
                type_value = property_type.value
            elif hasattr(property_type, "name"):
                type_value = property_type.name
            else:
                type_value = str(property_type)

            # Import PropertyType to check if it's DICT
            from aiecs.domain.knowledge_graph.schema.property_schema import PropertyType

            if type_value == PropertyType.DICT.value or type_value == "dict":
                # Get nested schema for next iteration
                nested_schema = self._get_nested_schema(property_schema)
                if nested_schema is None:
                    return None
                current_schema = nested_schema
            else:
                # Can't nest further
                return None

        return None

    def validate_relation_endpoints(
        self,
        relation_type: str,
        current_entity_type: str,
        direction: str,
        line: int,
        column: int,
    ) -> List[ValidationError]:
        """
        Validate that relation endpoints match entity types

        Args:
            relation_type: Relation type name
            current_entity_type: Current entity type in the query
            direction: Direction of traversal ("incoming" or "outgoing")
            line: Line number for error reporting
            column: Column number for error reporting

        Returns:
            List of validation errors
        """
        errors: List[ValidationError] = []

        # Get relation type schema
        if not hasattr(self.schema, "get_relation_type"):
            return errors

        relation_schema = self.schema.get_relation_type(relation_type)
        if relation_schema is None:
            return errors  # Relation type error already reported

        # Check if relation has endpoint constraints
        if not hasattr(relation_schema, "source_entity_types") or not hasattr(relation_schema, "target_entity_types"):
            return errors

        source_types = relation_schema.source_entity_types
        target_types = relation_schema.target_entity_types

        # Validate based on direction
        if direction == "outgoing":
            # Current entity is source, check if it's allowed
            if source_types and current_entity_type not in source_types:
                errors.append(
                    ValidationError(
                        line=line,
                        column=column,
                        message=f"Entity type '{current_entity_type}' cannot be source of relation '{relation_type}'",
                        suggestion=f"Allowed source types: {', '.join(source_types)}",
                    )
                )
        elif direction == "incoming":
            # Current entity is target, check if it's allowed
            if target_types and current_entity_type not in target_types:
                errors.append(
                    ValidationError(
                        line=line,
                        column=column,
                        message=f"Entity type '{current_entity_type}' cannot be target of relation '{relation_type}'",
                        suggestion=f"Allowed target types: {', '.join(target_types)}",
                    )
                )

        return errors
