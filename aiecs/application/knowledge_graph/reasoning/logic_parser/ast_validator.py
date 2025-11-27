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

        # Handle nested properties (e.g., "address.city")
        property_parts = property_path.split(".")
        current_property = property_parts[0]

        # Check if property exists
        if not hasattr(entity_schema, "get_property"):
            return errors

        property_schema = entity_schema.get_property(current_property)
        if property_schema is None:
            # Get available properties for suggestion
            available_props = []
            if hasattr(entity_schema, "properties"):
                available_props = list(entity_schema.properties.keys())

            suggestion = None
            if available_props:
                suggestion = f"Available properties for {entity_type}: {', '.join(available_props[:5])}"
                if len(available_props) > 5:
                    suggestion += f" (and {len(available_props) - 5} more)"

            errors.append(
                ValidationError(
                    line=line,
                    column=column,
                    message=f"Property '{current_property}' not found in entity type '{entity_type}'",
                    suggestion=suggestion,
                )
            )

        # TODO: Validate nested properties (requires nested schema support)

        return errors

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

        Args:
            entity_type: Entity type name
            property_path: Property path
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

        # Get property schema
        property_parts = property_path.split(".")
        current_property = property_parts[0]

        if not hasattr(entity_schema, "get_property"):
            return errors

        property_schema = entity_schema.get_property(current_property)
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
                                message=f"Property '{property_path}' expects {expected_type.__name__} values, " f"but list contains {type(item).__name__}",
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
                    message=f"Property '{property_path}' expects {expected_type.__name__} value, " f"got {type(value).__name__}",
                    suggestion=f"Use a {expected_type.__name__} value",
                )
            )

        return errors

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
