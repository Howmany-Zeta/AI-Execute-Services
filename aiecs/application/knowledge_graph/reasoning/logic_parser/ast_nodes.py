"""
AST Node Definitions for Logic Query Parser

This module defines the Abstract Syntax Tree (AST) node hierarchy for the Logic Query DSL.
Each node is self-contained and responsible for its own validation and conversion to QueryPlan.

Design Principles:
1. Self-Contained: Each node owns its complete structure (e.g., FindNode has filters)
2. Polymorphic Conversion: Each node implements its own to_query_plan() method
3. Immutable: Nodes are frozen dataclasses (cannot be modified after creation)
4. Type-Safe: Full type hints for all fields and methods

Phase: 2.4 - Logic Query Parser
Version: 1.0
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import uuid

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .query_context import QueryContext

# Import QueryPlan models
try:
    from aiecs.domain.knowledge_graph.models.query_plan import (
        QueryPlan,
        QueryStep,
        QueryOperation,
    )
    from aiecs.domain.knowledge_graph.models.query import GraphQuery, QueryType

    QUERY_PLAN_AVAILABLE = True
except ImportError:
    QUERY_PLAN_AVAILABLE = False
    # Use TYPE_CHECKING to avoid redefinition errors
    if TYPE_CHECKING:
        from typing import Any
        QueryPlan: Any  # type: ignore[assignment,no-redef]
        QueryStep: Any  # type: ignore[assignment,no-redef]
        QueryOperation: Any  # type: ignore[assignment,no-redef]
        GraphQuery: Any  # type: ignore[assignment,no-redef]
        QueryType: Any  # type: ignore[assignment,no-redef]
    else:
        from typing import Any
        QueryPlan = None  # type: ignore[assignment]
        QueryStep = None  # type: ignore[assignment]
        QueryOperation = None  # type: ignore[assignment]
        GraphQuery = None  # type: ignore[assignment]
        QueryType = None  # type: ignore[assignment]

# Placeholder for ValidationError (will be defined in error_handler.py)


@dataclass
class ValidationError:
    """Validation error with location information"""

    line: int
    column: int
    message: str
    suggestion: Optional[str] = None


@dataclass(frozen=True)
class ASTNode(ABC):
    """
    Base class for all AST nodes

    All AST nodes must:
    1. Store line/column metadata for error reporting
    2. Implement validate() for semantic validation
    3. Implement conversion to query plan (via to_query_plan or to_filter_dict)

    Attributes:
        line: Line number in source query (1-based)
        column: Column number in source query (1-based)
    """

    line: int
    column: int

    @abstractmethod
    def validate(self, schema: Any, entity_type: Optional[str] = None) -> List[ValidationError]:
        """
        Validate this node against the schema

        Args:
            schema: SchemaManager instance for validation
            entity_type: Optional entity type context for property validation

        Returns:
            List of validation errors (empty if valid)
        """


@dataclass(frozen=True)
class QueryNode(ASTNode):
    """
    Top-level query node: Find + optional Traversals + optional WHERE

    Represents a complete query with:
    - Required: FindNode for entity selection
    - Optional: List of TraversalNodes for graph navigation
    - Optional: WHERE clause (embedded in FindNode.filters)

    Example:
        Find(Person) FOLLOWS AuthoredBy WHERE year > 2020

        QueryNode(
            find=FindNode(entity_type="Person", ...),
            traversals=[TraversalNode(relation_type="AuthoredBy", ...)],
            ...
        )
    """

    find: "FindNode"
    traversals: List["TraversalNode"] = field(default_factory=list)

    def validate(self, schema: Any) -> List[ValidationError]:
        """Validate all parts of the query"""
        errors = []
        errors.extend(self.find.validate(schema))
        for traversal in self.traversals:
            errors.extend(traversal.validate(schema))
        return errors

    def to_query_plan(self, context: "QueryContext", original_query: str = "") -> Any:
        """
        Convert QueryNode to QueryPlan

        Creates a QueryPlan with multiple steps for complex queries with traversals.

        Args:
            context: Query context for variable resolution
            original_query: Original query string for documentation

        Returns:
            QueryPlan with one or more QuerySteps
        """
        if not QUERY_PLAN_AVAILABLE:
            raise ImportError("QueryPlan models not available")

        # Generate plan ID
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"

        # Convert to query steps
        steps = self.to_query_steps(context)

        # Create explanation
        explanation = self._generate_explanation()

        # Create QueryPlan
        plan = QueryPlan(
            plan_id=plan_id,
            original_query=original_query or str(self),
            steps=steps,
            explanation=explanation,
            optimized=False,
        )

        # Calculate total cost
        plan.total_estimated_cost = plan.calculate_total_cost()

        return plan

    def to_query_steps(self, context: "QueryContext") -> List[Any]:
        """
        Convert QueryNode to list of QuerySteps

        For simple queries (Find only), creates a single step.
        For complex queries (Find + Traversals), creates multiple steps.

        Args:
            context: Query context for variable resolution

        Returns:
            List of QueryStep objects
        """
        if not QUERY_PLAN_AVAILABLE:
            raise ImportError("QueryPlan models not available")

        steps = []

        # Step 1: Find entities (always present)
        find_step = self.find.to_query_step(context, step_id="step_1")
        steps.append(find_step)

        # Steps 2+: Traversals (if any)
        for i, traversal in enumerate(self.traversals, start=2):
            step_id = f"step_{i}"
            depends_on = [f"step_{i-1}"]  # Each step depends on previous
            traversal_step = traversal.to_query_step(context, step_id=step_id, depends_on=depends_on)
            steps.append(traversal_step)

        return steps

    def _generate_explanation(self) -> str:
        """Generate human-readable explanation of the query"""
        parts = [f"Find {self.find.entity_type} entities"]

        if self.find.entity_name:
            parts.append(f"named '{self.find.entity_name}'")

        if self.find.filters:
            parts.append(f"with {len(self.find.filters)} filter(s)")

        if self.traversals:
            parts.append(f"then traverse {len(self.traversals)} relation(s)")

        return " ".join(parts)

    def __repr__(self) -> str:
        """String representation for debugging"""
        traversals_str = f", traversals={len(self.traversals)}" if self.traversals else ""
        return f"QueryNode(find={self.find}{traversals_str})"


@dataclass(frozen=True)
class FindNode(ASTNode):
    """
    Entity selection node: Find(EntityType) or Find(EntityType[`Name`])

    Represents entity selection with optional filters.
    This node is self-contained and owns its filters.

    Attributes:
        entity_type: Type of entity to find (e.g., "Person", "Paper")
        entity_name: Optional specific entity name (e.g., "Alice")
        filters: List of filter nodes (from WHERE clause)

    Example:
        Find(Person[`Alice`]) WHERE age > 30

        FindNode(
            entity_type="Person",
            entity_name="Alice",
            filters=[PropertyFilterNode(property="age", operator=">", value=30)]
        )
    """

    entity_type: str
    entity_name: Optional[str] = None
    filters: List["FilterNode"] = field(default_factory=list)

    def validate(self, schema: Any, entity_type: Optional[str] = None) -> List[ValidationError]:
        """
        Validate entity type and all filters
        
        Args:
            schema: Schema object for validation
            entity_type: Optional entity type (uses self.entity_type if not provided)
        """
        errors = []

        # Use self.entity_type if entity_type parameter not provided
        effective_entity_type = entity_type if entity_type is not None else self.entity_type

        # Validate entity type exists (if schema has this method)
        if hasattr(schema, "has_entity_type"):
            if not schema.has_entity_type(effective_entity_type):
                errors.append(
                    ValidationError(
                        self.line,
                        self.column,
                        f"Entity type '{effective_entity_type}' not found",
                        suggestion=f"Available types: {', '.join(schema.get_entity_types())}",
                    )
                )

        # Validate all filters (pass entity_type for property validation)
        for filter_node in self.filters:
            errors.extend(filter_node.validate(schema, entity_type=effective_entity_type))

        return errors

    def to_query_step(
        self,
        context: "QueryContext",
        step_id: str = "step_1",
        depends_on: Optional[List[str]] = None,
    ) -> Any:
        """
        Convert FindNode to QueryStep

        Creates a QueryStep for entity lookup/filter operation.

        Args:
            context: Query context for variable resolution
            step_id: Unique identifier for this step
            depends_on: List of step IDs this step depends on

        Returns:
            QueryStep for entity lookup/filter
        """
        if not QUERY_PLAN_AVAILABLE:
            raise ImportError("QueryPlan models not available")

        # Build property filters
        properties = {}
        if self.filters:
            # Combine all filters into a single filter dict
            for filter_node in self.filters:
                filter_dict = filter_node.to_filter_dict(context)
                properties.update(filter_dict)

        # Determine query type and operation
        # If entity_name is provided, it's an entity lookup
        # Otherwise, it's a filter operation
        if self.entity_name:
            query_type = QueryType.ENTITY_LOOKUP
            operation = QueryOperation.ENTITY_LOOKUP
        else:
            # For filter operations, we use ENTITY_LOOKUP query type with
            # filters
            query_type = QueryType.ENTITY_LOOKUP
            operation = QueryOperation.FILTER

        # Create GraphQuery
        query = GraphQuery(
            query_type=query_type,
            entity_type=self.entity_type,
            entity_id=self.entity_name,  # If specific entity name is provided
            properties=properties,
            max_results=100,  # Default limit
        )

        # Create description
        description = f"Find {self.entity_type} entities"
        if self.entity_name:
            description += f" named '{self.entity_name}'"
        if self.filters:
            description += f" with {len(self.filters)} filter(s)"

        # Create QueryStep
        step = QueryStep(
            step_id=step_id,
            operation=operation,
            query=query,
            depends_on=depends_on or [],
            description=description,
            estimated_cost=0.3,  # Low cost for simple entity lookup
        )

        return step

    def __repr__(self) -> str:
        """String representation for debugging"""
        name_str = f"[`{self.entity_name}`]" if self.entity_name else ""
        filters_str = f", filters={len(self.filters)}" if self.filters else ""
        return f"FindNode({self.entity_type}{name_str}{filters_str})"


@dataclass(frozen=True)
class TraversalNode(ASTNode):
    """
    Graph traversal node: FOLLOWS RelationType [direction]

    Represents navigation along graph relationships.

    Attributes:
        relation_type: Type of relation to follow (e.g., "AuthoredBy")
        direction: Direction of traversal ("outgoing", "incoming", or None for default)

    Example:
        FOLLOWS AuthoredBy INCOMING

        TraversalNode(
            relation_type="AuthoredBy",
            direction="incoming"
        )
    """

    relation_type: str
    direction: Optional[str] = "outgoing"  # "incoming" | "outgoing" | None

    def validate(self, schema: Any, entity_type: Optional[str] = None) -> List[ValidationError]:
        """
        Validate relation type exists
        
        Args:
            schema: Schema object for validation
            entity_type: Optional entity type (not used for traversal validation)
        """
        errors = []

        # Validate relation type exists (if schema has this method)
        if hasattr(schema, "has_relation_type"):
            if not schema.has_relation_type(self.relation_type):
                errors.append(
                    ValidationError(
                        self.line,
                        self.column,
                        f"Relation type '{self.relation_type}' not found",
                    )
                )

        # Validate direction
        if self.direction and self.direction not in ["incoming", "outgoing"]:
            errors.append(
                ValidationError(
                    self.line,
                    self.column,
                    f"Invalid direction '{self.direction}'. Must be 'incoming' or 'outgoing'",
                )
            )

        return errors

    def to_query_step(self, context: "QueryContext", step_id: str, depends_on: List[str]) -> Any:
        """
        Convert TraversalNode to QueryStep

        Creates a QueryStep for graph traversal operation.

        Args:
            context: Query context for variable resolution
            step_id: Unique identifier for this step
            depends_on: List of step IDs this step depends on

        Returns:
            QueryStep for graph traversal
        """
        if not QUERY_PLAN_AVAILABLE:
            raise ImportError("QueryPlan models not available")

        # Create GraphQuery for traversal
        query = GraphQuery(
            query_type=QueryType.TRAVERSAL,
            relation_type=self.relation_type,
            max_depth=1,  # Single hop traversal
            max_results=100,  # Default limit
        )

        # Create description
        direction_str = self.direction.upper() if self.direction else "OUTGOING"
        description = f"Traverse {self.relation_type} relation ({direction_str})"

        # Create QueryStep
        step = QueryStep(
            step_id=step_id,
            operation=QueryOperation.TRAVERSAL,
            query=query,
            depends_on=depends_on,
            description=description,
            estimated_cost=0.5,  # Medium cost for traversal
            metadata={"direction": self.direction or "outgoing"},
        )

        return step

    def __repr__(self) -> str:
        """String representation for debugging"""
        dir_str = f" {self.direction.upper()}" if self.direction else ""
        return f"TraversalNode({self.relation_type}{dir_str})"


@dataclass(frozen=True)
class FilterNode(ASTNode):
    """
    Base class for filter nodes (WHERE conditions)

    Filter nodes represent conditions in WHERE clauses.
    They convert to filter dictionaries (MongoDB-style) for query execution.

    Subclasses:
    - PropertyFilterNode: property operator value (e.g., age > 30)
    - BooleanFilterNode: AND/OR/NOT combinations
    """

    @abstractmethod
    def to_filter_dict(self, context: "QueryContext") -> Dict[str, Any]:
        """
        Convert filter to MongoDB-style filter dictionary

        Args:
            context: Query context for variable resolution

        Returns:
            Filter dictionary (e.g., {"age": {"$gt": 30}})
        """


@dataclass(frozen=True)
class PropertyFilterNode(FilterNode):
    """
    Property filter node: property operator value

    Represents a comparison between a property and a value.

    Attributes:
        property_path: Property name or nested path (e.g., "age" or "address.city")
        operator: Comparison operator (==, !=, >, <, >=, <=, IN, CONTAINS)
        value: Value to compare against

    Example:
        age > 30

        PropertyFilterNode(
            property_path="age",
            operator=">",
            value=30
        )
    """

    property_path: str  # Can be nested: "address.city"
    operator: str  # "==", "!=", ">", "<", ">=", "<=", "IN", "CONTAINS"
    value: Any

    def to_filter_dict(self, context: "QueryContext") -> Dict[str, Any]:
        """Convert to MongoDB-style filter dict"""
        operator_map = {
            "==": "$eq",
            "!=": "$ne",
            ">": "$gt",
            "<": "$lt",
            ">=": "$gte",
            "<=": "$lte",
            "IN": "$in",
            "CONTAINS": "$regex",
        }

        mongo_op = operator_map.get(self.operator, "$eq")

        # For CONTAINS, convert to regex pattern
        if self.operator == "CONTAINS":
            return {self.property_path: {mongo_op: self.value}}

        return {self.property_path: {mongo_op: self.value}}

    def validate(self, schema: Any, entity_type: Optional[str] = None) -> List[ValidationError]:
        """
        Validate property exists and type matches
        
        Args:
            schema: Schema object for validation
            entity_type: Optional entity type context for property validation
        """
        errors = []

        # Validate operator is valid
        valid_operators = ["==", "!=", ">", "<", ">=", "<=", "IN", "CONTAINS"]
        if self.operator not in valid_operators:
            errors.append(
                ValidationError(
                    self.line,
                    self.column,
                    f"Invalid operator '{self.operator}'. Must be one of: {', '.join(valid_operators)}",
                )
            )

        # Validate IN operator has list value
        if self.operator == "IN" and not isinstance(self.value, list):
            errors.append(
                ValidationError(
                    self.line,
                    self.column,
                    f"IN operator requires a list value, got {type(self.value).__name__}",
                )
            )

        # Validate CONTAINS operator has string value
        if self.operator == "CONTAINS" and not isinstance(self.value, str):
            errors.append(
                ValidationError(
                    self.line,
                    self.column,
                    f"CONTAINS operator requires a string value, got {type(self.value).__name__}",
                )
            )

        # Validate property exists in schema (if entity_type provided)
        if entity_type:
            errors.extend(self._validate_property_in_schema(schema, entity_type))
        else:
            logger.debug(
                f"PropertyFilterNode.validate: "
                f"FALLBACK - No entity_type provided, skipping property validation for '{self.property_path}'"
            )

        return errors

    def _validate_property_in_schema(self, schema: Any, entity_type: str) -> List[ValidationError]:
        """
        Validate that property exists in entity type schema
        
        Args:
            schema: Schema object for validation
            entity_type: Entity type to validate against
            
        Returns:
            List of validation errors
        """
        errors = []

        # Check if schema has required methods
        if not hasattr(schema, "get_entity_type"):
            logger.debug(
                f"PropertyFilterNode._validate_property_in_schema: "
                f"FALLBACK - schema missing 'get_entity_type' method, skipping property validation"
            )
            return errors

        # Get entity type schema
        entity_schema = schema.get_entity_type(entity_type)
        if entity_schema is None:
            # Entity type doesn't exist - error already reported by FindNode
            logger.debug(
                f"PropertyFilterNode._validate_property_in_schema: "
                f"FALLBACK - entity type '{entity_type}' not found in schema, skipping property validation"
            )
            return errors

        # Validate nested property path recursively
        errors.extend(
            self._validate_nested_property_path(
                entity_schema=entity_schema,
                property_path=self.property_path,
                entity_type=entity_type,
                current_path="",
            )
        )

        return errors

    def _validate_nested_property_path(
        self,
        entity_schema: Any,
        property_path: str,
        entity_type: str,
        current_path: str = "",
    ) -> List[ValidationError]:
        """
        Recursively validate a nested property path

        Args:
            entity_schema: Current entity schema (may be nested)
            property_path: Remaining property path to validate
            entity_type: Root entity type name
            current_path: Accumulated path so far (for error messages)

        Returns:
            List of validation errors
        """
        errors = []

        # Split property path into parts
        property_parts = property_path.split(".")
        current_property = property_parts[0]
        remaining_path = ".".join(property_parts[1:]) if len(property_parts) > 1 else None

        # Build full path for error messages
        full_path = f"{current_path}.{current_property}" if current_path else current_property

        # Check if entity schema has get_property method
        if not hasattr(entity_schema, "get_property"):
            logger.debug(
                f"PropertyFilterNode._validate_nested_property_path: "
                f"FALLBACK - entity_schema missing 'get_property' method for '{entity_type}', "
                f"skipping nested property validation at '{full_path}'"
            )
            return errors

        # Get property schema
        property_schema = entity_schema.get_property(current_property)
        if property_schema is None:
            # Property doesn't exist - get available properties for suggestion
            available_props = []
            if hasattr(entity_schema, "properties"):
                available_props = list(entity_schema.properties.keys())
                logger.debug(
                    f"PropertyFilterNode._validate_nested_property_path: "
                    f"Using 'properties' attribute to get available properties for '{entity_type}'"
                )
            elif hasattr(entity_schema, "get_property_names"):
                available_props = entity_schema.get_property_names()
                logger.debug(
                    f"PropertyFilterNode._validate_nested_property_path: "
                    f"FALLBACK - Using 'get_property_names()' method instead of 'properties' attribute "
                    f"for '{entity_type}'"
                )

            suggestion = None
            if available_props:
                context = f"{entity_type}.{current_path}" if current_path else entity_type
                suggestion = f"Available properties for {context}: {', '.join(available_props[:5])}"
                if len(available_props) > 5:
                    suggestion += f" (and {len(available_props) - 5} more)"

            errors.append(
                ValidationError(
                    self.line,
                    self.column,
                    f"Property '{full_path}' not found in {entity_type if not current_path else current_path}",
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
                        self.line,
                        self.column,
                        f"Cannot validate nested path '{full_path}.{remaining_path}': "
                        f"property '{current_property}' type unknown",
                        suggestion="Ensure property schema defines property_type",
                    )
                )
                return errors

            property_type = property_schema.property_type

            # Check if property type supports nesting
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
                            self.line,
                            self.column,
                            f"Cannot validate nested path '{full_path}.{remaining_path}': "
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
                        current_path=full_path,
                    )
                )
            else:
                # Property is not DICT type - can't nest further
                errors.append(
                    ValidationError(
                        self.line,
                        self.column,
                        f"Cannot access nested path '{full_path}.{remaining_path}': "
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

    def __repr__(self) -> str:
        """String representation for debugging"""
        value_repr = f'"{self.value}"' if isinstance(self.value, str) else str(self.value)
        return f"PropertyFilterNode({self.property_path} {self.operator} {value_repr})"


@dataclass(frozen=True)
class BooleanFilterNode(FilterNode):
    """
    Boolean filter node: AND/OR/NOT combinations

    Represents boolean combinations of filters.

    Attributes:
        operator: Boolean operator ("AND", "OR", "NOT")
        operands: List of filter nodes to combine

    Example:
        age > 30 AND status == "active"

        BooleanFilterNode(
            operator="AND",
            operands=[
                PropertyFilterNode(property_path="age", operator=">", value=30),
                PropertyFilterNode(property_path="status", operator="==", value="active")
            ]
        )
    """

    operator: str  # "AND", "OR", "NOT"
    operands: List[FilterNode] = field(default_factory=list)

    def to_filter_dict(self, context: "QueryContext") -> Dict[str, Any]:
        """Convert to MongoDB-style boolean filter"""
        op_map = {"AND": "$and", "OR": "$or", "NOT": "$not"}

        mongo_op = op_map.get(self.operator, "$and")
        operand_dicts = [op.to_filter_dict(context) for op in self.operands]

        # NOT operator has special handling (single operand)
        if self.operator == "NOT":
            if len(operand_dicts) == 1:
                return {mongo_op: operand_dicts[0]}
            else:
                # Multiple operands: NOT (a AND b AND c) = NOT {$and: [a, b,
                # c]}
                return {mongo_op: {"$and": operand_dicts}}

        return {mongo_op: operand_dicts}

    def validate(self, schema: Any, entity_type: Optional[str] = None) -> List[ValidationError]:
        """
        Validate all operands
        
        Args:
            schema: Schema object for validation
            entity_type: Optional entity type context for property validation
        """
        errors = []

        # Validate operator is valid
        valid_operators = ["AND", "OR", "NOT"]
        if self.operator not in valid_operators:
            errors.append(
                ValidationError(
                    self.line,
                    self.column,
                    f"Invalid boolean operator '{self.operator}'. Must be one of: {', '.join(valid_operators)}",
                )
            )

        # Validate operand count
        if not self.operands:
            errors.append(
                ValidationError(
                    self.line,
                    self.column,
                    f"Boolean operator '{self.operator}' requires at least one operand",
                )
            )

        # Validate all operands (pass entity_type for property validation)
        for operand in self.operands:
            errors.extend(operand.validate(schema, entity_type=entity_type))

        return errors

    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"BooleanFilterNode({self.operator}, operands={len(self.operands)})"
