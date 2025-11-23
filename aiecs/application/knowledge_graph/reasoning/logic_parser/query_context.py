"""
Query Context for Logic Query Parser

This module provides the QueryContext class for managing state during query parsing
and conversion. The context is used to track variables, errors, and query steps.

**IMPORTANT**: QueryContext is NOT thread-safe. Create a new instance for each parse request.

Phase: 2.4 - Logic Query Parser
Version: 1.0
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


class VariableRedefinitionError(Exception):
    """Raised when attempting to redefine an already-bound variable"""


class UndefinedVariableError(Exception):
    """Raised when attempting to resolve an undefined variable"""


@dataclass
class QueryContext:
    """
    Context for query parsing and conversion

    This class manages state during query parsing, including:
    - Schema reference for validation
    - Variable bindings for multi-step queries
    - Error accumulation for validation
    - Query steps for multi-step query construction

    **Thread Safety**: This class contains mutable state and is NOT thread-safe.
    Create a NEW QueryContext instance for EACH parse request.

    **Lifecycle**:
    1. Create: `context = QueryContext(schema)`
    2. Use: `ast.to_query_plan(context)` or `ast.validate(schema)`
    3. Discard: Context should not be reused for another query

    **Concurrency Pattern**:
    ```python
    # ✅ CORRECT: New context per request
    def parse_concurrent(query: str):
        context = QueryContext(schema)  # Fresh instance
        return parser.parse(query, context)

    # ❌ WRONG: Shared context across requests
    shared_context = QueryContext(schema)  # DON'T DO THIS
    def parse_concurrent(query: str):
        return parser.parse(query, shared_context)  # Race condition!
    ```

    Attributes:
        schema: Schema manager for validation (immutable reference)
        variables: Variable bindings for multi-step queries (mutable)
        query_steps: Accumulated query steps (mutable)
        errors: Accumulated validation errors (mutable)

    Example:
        ```python
        schema = SchemaManager()
        context = QueryContext(schema)

        # Bind a variable
        context.bind_variable("person_id", "123")

        # Resolve a variable
        person_id = context.resolve_variable("person_id")

        # Add an error
        context.add_error(ParserError(...))

        # Clear context for reuse (not recommended)
        context.clear()
        ```
    """

    # SchemaManager instance (type hint as Any to avoid circular import)
    schema: Any
    variables: Dict[str, Any] = field(default_factory=dict)
    query_steps: List[Any] = field(default_factory=list)  # List[QueryStep]
    errors: List[Any] = field(default_factory=list)  # List[ParserError]

    def bind_variable(self, name: str, value: Any) -> None:
        """
        Bind a variable to a value

        Variables are used in multi-step queries to reference results from
        previous steps.

        Args:
            name: Variable name (must be unique)
            value: Value to bind to the variable

        Raises:
            VariableRedefinitionError: If variable is already bound

        Example:
            ```python
            context.bind_variable("person_id", "123")
            context.bind_variable("person_id", "456")  # Raises error
            ```
        """
        if name in self.variables:
            raise VariableRedefinitionError(f"Variable '{name}' is already defined with value: {self.variables[name]}")
        self.variables[name] = value

    def resolve_variable(self, name: str) -> Any:
        """
        Resolve a variable to its value

        Args:
            name: Variable name to resolve

        Returns:
            Value bound to the variable

        Raises:
            UndefinedVariableError: If variable is not bound

        Example:
            ```python
            context.bind_variable("person_id", "123")
            value = context.resolve_variable("person_id")  # Returns "123"
            value = context.resolve_variable("unknown")  # Raises error
            ```
        """
        if name not in self.variables:
            raise UndefinedVariableError(f"Variable '{name}' is not defined. Available variables: {list(self.variables.keys())}")
        return self.variables[name]

    def add_error(self, error: Any) -> None:
        """
        Add a validation or parsing error to the context

        Errors are accumulated during parsing and validation so that
        multiple errors can be reported at once.

        Args:
            error: ParserError or ValidationError instance

        Example:
            ```python
            error = ParserError(line=1, column=10, message="Invalid syntax")
            context.add_error(error)
            ```
        """
        self.errors.append(error)

    def clear(self) -> None:
        """
        Clear all mutable state in the context

        This method resets variables, query steps, and errors.

        **WARNING**: Reusing a context is NOT recommended. Create a new
        context for each parse request instead.

        Example:
            ```python
            context.clear()  # Reset all state
            ```
        """
        self.variables.clear()
        self.query_steps.clear()
        self.errors.clear()

    def has_variable(self, name: str) -> bool:
        """
        Check if a variable is bound

        Args:
            name: Variable name to check

        Returns:
            True if variable is bound, False otherwise

        Example:
            ```python
            context.bind_variable("person_id", "123")
            assert context.has_variable("person_id") == True
            assert context.has_variable("unknown") == False
            ```
        """
        return name in self.variables

    def has_errors(self) -> bool:
        """
        Check if any errors have been accumulated

        Returns:
            True if errors exist, False otherwise

        Example:
            ```python
            if context.has_errors():
                print(f"Found {len(context.errors)} errors")
            ```
        """
        return len(self.errors) > 0

    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"QueryContext(" f"variables={len(self.variables)}, " f"steps={len(self.query_steps)}, " f"errors={len(self.errors)})"
