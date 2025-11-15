"""
AST Builder for Logic Query Parser

This module provides the ASTBuilder class that transforms Lark parse trees
into AST nodes. It extends lark.Transformer to convert parse tree nodes
into our custom AST node hierarchy.

Design Principles:
1. Each transformation method corresponds to a grammar rule
2. Line/column metadata is preserved from parse tree
3. Transformations are composable (bottom-up)
4. Type-safe conversions with proper error handling

Phase: 2.4 - Logic Query Parser
Task: 2.2 - Implement AST Builder
Version: 1.0
"""

from typing import Any, List, Union
from lark import Transformer, Token

from .ast_nodes import (
    QueryNode,
    FindNode,
    TraversalNode,
    FilterNode,
    PropertyFilterNode,
    BooleanFilterNode,
)


class ASTBuilder(Transformer):
    """
    Transform Lark parse tree into AST nodes

    This class extends lark.Transformer to convert parse tree nodes
    into our custom AST node hierarchy. Each method corresponds to
    a grammar rule and returns the appropriate AST node.

    **Transformation Flow**:
    1. Lark parses query string → parse tree
    2. ASTBuilder.transform(parse_tree) → AST
    3. Bottom-up transformation (leaves first, then parents)

    **Line/Column Metadata**:
    - Extracted from Token.line and Token.column
    - Preserved in all AST nodes for error reporting

    Example:
        ```python
        from lark import Lark

        parser = Lark(grammar, start='query')
        builder = ASTBuilder()

        parse_tree = parser.parse("Find(Person) WHERE age > 30")
        ast = builder.transform(parse_tree)

        # ast is now a QueryNode with FindNode and filters
        ```
    """

    def __init__(self):
        """Initialize AST builder"""
        super().__init__()

    def negate(self, items: List[Any]) -> BooleanFilterNode:
        """
        Transform negate rule: "NOT" not_condition

        This is called when the grammar matches "NOT" not_condition.

        Args:
            items: [condition to negate]

        Returns:
            BooleanFilterNode with NOT operator
        """
        condition = items[0]

        # Get line/column from the condition
        line = getattr(condition, "line", 1)
        column = getattr(condition, "column", 1)

        return BooleanFilterNode(line=line, column=column, operator="NOT", operands=[condition])

    # ========================================================================
    # Top-Level Query Transformation
    # ========================================================================

    def query(self, items: List[Any]) -> QueryNode:
        """
        Transform query rule: find_clause traversal_clause* where_clause?

        Args:
            items: List of transformed children
                   [0] = FindNode
                   [1:] = TraversalNodes (if any)

        Returns:
            QueryNode with find and traversals
        """
        find_node = items[0]
        traversals = []

        # Collect traversal nodes (if any)
        for item in items[1:]:
            if isinstance(item, TraversalNode):
                traversals.append(item)
            elif isinstance(item, list):
                # where_clause returns list of filters
                # Attach filters to FindNode
                # Note: FindNode is frozen, so we need to create a new one
                find_node = FindNode(
                    line=find_node.line,
                    column=find_node.column,
                    entity_type=find_node.entity_type,
                    entity_name=find_node.entity_name,
                    filters=item,
                )

        # Get line/column from find_node
        return QueryNode(
            line=find_node.line,
            column=find_node.column,
            find=find_node,
            traversals=traversals,
        )

    # ========================================================================
    # Find Clause Transformation
    # ========================================================================

    def find_clause(self, items: List[Any]) -> FindNode:
        """
        Transform find_clause rule: "Find" "(" entity_spec ")"

        Args:
            items: List with entity_spec (tuple of entity_type, entity_name)

        Returns:
            FindNode with entity type and optional name
        """
        entity_type, entity_name, line, column = items[0]

        return FindNode(
            line=line,
            column=column,
            entity_type=entity_type,
            entity_name=entity_name,
            filters=[],  # Filters added later by query rule
        )

    def entity_spec(self, items: List[Any]) -> tuple:
        """
        Transform entity_spec rule: IDENTIFIER ("[" entity_name "]")?

        Args:
            items: [IDENTIFIER, optional entity_name]

        Returns:
            Tuple of (entity_type, entity_name, line, column)
        """
        entity_type_token = items[0]
        entity_type = str(entity_type_token)
        entity_name = None

        # Check if entity name is provided
        if len(items) > 1:
            entity_name = items[1]

        return (
            entity_type,
            entity_name,
            entity_type_token.line,
            entity_type_token.column,
        )

    def entity_name(self, items: List[Any]) -> str:
        """
        Transform entity_name rule: BACKTICK_STRING

        Args:
            items: [BACKTICK_STRING token]

        Returns:
            Entity name without backticks
        """
        backtick_string = str(items[0])
        # Remove backticks
        return backtick_string.strip("`")

    # ========================================================================
    # Traversal Clause Transformation
    # ========================================================================

    def traversal_clause(self, items: List[Any]) -> TraversalNode:
        """
        Transform traversal_clause rule: "FOLLOWS" relation_spec direction?

        Args:
            items: [relation_type, optional direction]

        Returns:
            TraversalNode with relation type and direction
        """
        relation_type_token = items[0]
        relation_type = str(relation_type_token)
        direction = "outgoing"  # Default

        # Check if direction is provided
        if len(items) > 1:
            direction = items[1]

        return TraversalNode(
            line=relation_type_token.line,
            column=relation_type_token.column,
            relation_type=relation_type,
            direction=direction,
        )

    def relation_spec(self, items: List[Any]) -> Token:
        """
        Transform relation_spec rule: IDENTIFIER

        Args:
            items: [IDENTIFIER token]

        Returns:
            IDENTIFIER token (passed through for line/column info)
        """
        return items[0]

    def incoming(self, items: List[Any]) -> str:
        """Transform INCOMING direction"""
        return "incoming"

    def outgoing(self, items: List[Any]) -> str:
        """Transform OUTGOING direction"""
        return "outgoing"

    # ========================================================================
    # Where Clause Transformation
    # ========================================================================

    def where_clause(self, items: List[Any]) -> List[FilterNode]:
        """
        Transform where_clause rule: "WHERE" condition

        Args:
            items: [condition (FilterNode or list of FilterNodes)]

        Returns:
            List of FilterNodes
        """
        condition = items[0]

        # Wrap single filter in list
        if isinstance(condition, FilterNode):
            return [condition]
        elif isinstance(condition, list):
            return condition
        else:
            return [condition]

    # ========================================================================
    # Condition Transformation (Boolean Logic)
    # ========================================================================

    def or_condition(self, items: List[Any]) -> FilterNode:
        """
        Transform or_condition rule: and_condition ("OR" and_condition)*

        Args:
            items: List of and_conditions

        Returns:
            BooleanFilterNode with OR operator (if multiple items)
            or single FilterNode (if one item)
        """
        if len(items) == 1:
            return items[0]

        # Multiple items: create OR node
        first_item = items[0]
        return BooleanFilterNode(
            line=first_item.line if hasattr(first_item, "line") else 1,
            column=first_item.column if hasattr(first_item, "column") else 1,
            operator="OR",
            operands=items,
        )

    def and_condition(self, items: List[Any]) -> FilterNode:
        """
        Transform and_condition rule: not_condition ("AND" not_condition)*

        Args:
            items: List of not_conditions

        Returns:
            BooleanFilterNode with AND operator (if multiple items)
            or single FilterNode (if one item)
        """
        if len(items) == 1:
            return items[0]

        # Multiple items: create AND node
        first_item = items[0]
        return BooleanFilterNode(
            line=first_item.line if hasattr(first_item, "line") else 1,
            column=first_item.column if hasattr(first_item, "column") else 1,
            operator="AND",
            operands=items,
        )

    def not_condition(self, items: List[Any]) -> FilterNode:
        """
        Transform not_condition rule: "NOT" not_condition -> negate | primary_condition

        This method is called for the primary_condition branch (pass-through).
        The "NOT" branch is handled by the negate() method.

        Args:
            items: [primary_condition]

        Returns:
            FilterNode (passed through)
        """
        return items[0]

    def primary_condition(self, items: List[Any]) -> FilterNode:
        """
        Transform primary_condition rule: "(" condition ")" | simple_condition

        Args:
            items: [condition] (parenthesized or simple)

        Returns:
            FilterNode
        """
        return items[0]

    # ========================================================================
    # Simple Condition Transformation
    # ========================================================================

    def simple_condition(self, items: List[Any]) -> PropertyFilterNode:
        """
        Transform simple_condition rule: property_path operator value

        Args:
            items: [property_path, operator, value]

        Returns:
            PropertyFilterNode
        """
        property_path = items[0]
        operator = items[1]
        value = items[2]

        # Get line/column from property_path token
        if isinstance(property_path, str):
            line, column = 1, 1
        else:
            line = getattr(property_path, "line", 1)
            column = getattr(property_path, "column", 1)
            property_path = str(property_path)

        return PropertyFilterNode(
            line=line,
            column=column,
            property_path=property_path,
            operator=operator,
            value=value,
        )

    def property_path(self, items: List[Any]) -> str:
        """
        Transform property_path rule: IDENTIFIER ("." IDENTIFIER)*

        Args:
            items: List of IDENTIFIER tokens

        Returns:
            Dot-separated property path string
        """
        # Join identifiers with dots for nested properties
        path_parts = [str(item) for item in items]
        return ".".join(path_parts)

    # ========================================================================
    # Operator Transformation
    # ========================================================================

    def eq(self, items: List[Any]) -> str:
        """Transform == operator"""
        return "=="

    def ne(self, items: List[Any]) -> str:
        """Transform != operator"""
        return "!="

    def gt(self, items: List[Any]) -> str:
        """Transform > operator"""
        return ">"

    def lt(self, items: List[Any]) -> str:
        """Transform < operator"""
        return "<"

    def gte(self, items: List[Any]) -> str:
        """Transform >= operator"""
        return ">="

    def lte(self, items: List[Any]) -> str:
        """Transform <= operator"""
        return "<="

    def in_op(self, items: List[Any]) -> str:
        """Transform IN operator"""
        return "IN"

    def contains(self, items: List[Any]) -> str:
        """Transform CONTAINS operator"""
        return "CONTAINS"

    # ========================================================================
    # Value Transformation
    # ========================================================================

    def string_value(self, items: List[Any]) -> str:
        """
        Transform string_value rule: STRING

        Args:
            items: [STRING token]

        Returns:
            String value without quotes
        """
        string_token = str(items[0])
        # Remove quotes (single or double)
        return string_token.strip("\"'")

    def number_value(self, items: List[Any]) -> Union[int, float]:
        """
        Transform number_value rule: NUMBER

        Args:
            items: [NUMBER token]

        Returns:
            Integer or float value
        """
        number_str = str(items[0])

        # Try to parse as int first, then float
        if "." in number_str:
            return float(number_str)
        else:
            return int(number_str)

    def boolean_value(self, items: List[Any]) -> bool:
        """
        Transform boolean_value rule: BOOLEAN

        Args:
            items: [BOOLEAN token]

        Returns:
            Boolean value
        """
        if not items:
            return False

        bool_str = str(items[0]).lower().strip()
        return bool_str in ("true", "t", "1")

    def list_value(self, items: List[Any]) -> List[Any]:
        """
        Transform list_value rule: list

        Args:
            items: [list of values]

        Returns:
            List of values
        """
        return items[0] if items else []

    def list(self, items: List[Any]) -> List[Any]:
        """
        Transform list rule: "[" [value ("," value)*] "]"

        Args:
            items: List of values

        Returns:
            List of values
        """
        return items

    def identifier_value(self, items: List[Any]) -> str:
        """
        Transform identifier_value rule: IDENTIFIER

        Args:
            items: [IDENTIFIER token]

        Returns:
            Identifier string (for variable references)
        """
        return str(items[0])
