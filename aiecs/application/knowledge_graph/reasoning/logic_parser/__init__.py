"""
Logic Query Parser

Parses declarative query DSL into executable query plans for knowledge graph reasoning.

This package provides:
- Grammar definition (Lark EBNF)
- AST node definitions
- Parser implementation
- Query plan conversion
- Error handling

Example:
    ```python
    from aiecs.application.knowledge_graph.reasoning.logic_parser import LogicQueryParser

    parser = LogicQueryParser(schema)
    result = parser.parse_to_query_plan("Find(Person) WHERE age > 30")

    if isinstance(result, QueryPlan):
        # Execute the plan
        planner.execute(result)
    else:
        # Handle errors
        for error in result:
            print(f"Error at line {error.line}: {error.message}")
    ```

Phase: 2.4 - Logic Query Parser
Version: 1.0
"""

__version__ = "1.0.0"
__phase__ = "2.4"

# Export main components
from .parser import LogicQueryParser
from .error_handler import ParserError, ErrorHandler
from .ast_nodes import (
    ASTNode,
    QueryNode,
    FindNode,
    TraversalNode,
    FilterNode,
    PropertyFilterNode,
    BooleanFilterNode,
    ValidationError,
)
from .query_context import (
    QueryContext,
    VariableRedefinitionError,
    UndefinedVariableError,
)
from .ast_builder import ASTBuilder
from .ast_validator import ASTValidator

__all__ = [
    # Parser
    "LogicQueryParser",
    "ParserError",
    "ErrorHandler",
    # AST Nodes
    "ASTNode",
    "QueryNode",
    "FindNode",
    "TraversalNode",
    "FilterNode",
    "PropertyFilterNode",
    "BooleanFilterNode",
    "ValidationError",
    # AST Builder
    "ASTBuilder",
    # AST Validator
    "ASTValidator",
    # Context
    "QueryContext",
    "VariableRedefinitionError",
    "UndefinedVariableError",
]
