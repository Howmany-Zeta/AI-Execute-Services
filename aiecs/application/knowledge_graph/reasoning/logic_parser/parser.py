"""
Logic Query Parser

This module provides the LogicQueryParser class for parsing Logic Query DSL
into Abstract Syntax Trees (AST).

The parser uses Lark for syntax parsing and implements two-phase error handling:
- Phase 1: Syntax parsing (fatal errors from Lark)
- Phase 2: Semantic validation (accumulated errors from AST)

Phase: 2.4 - Logic Query Parser
Version: 1.0
"""

from pathlib import Path
from typing import Union, List, Any, Optional, Dict
from functools import lru_cache

try:
    from lark import (
        Lark,
        LarkError,
        UnexpectedInput,
        UnexpectedToken,
        UnexpectedCharacters,
    )

    LARK_AVAILABLE = True
except ImportError:
    LARK_AVAILABLE = False
    from typing import Any, TYPE_CHECKING
    if TYPE_CHECKING:
        Lark: Any  # type: ignore[assignment,no-redef]
        LarkError: Any  # type: ignore[assignment,no-redef]
        UnexpectedInput: Any  # type: ignore[assignment,no-redef]
        UnexpectedToken: Any  # type: ignore[assignment,no-redef]
        UnexpectedCharacters: Any  # type: ignore[assignment,no-redef]
    else:
        Lark = None  # type: ignore[assignment]
        LarkError = Exception  # type: ignore[assignment]
        UnexpectedInput = Exception  # type: ignore[assignment]
        UnexpectedToken = Exception  # type: ignore[assignment]
        UnexpectedCharacters = Exception  # type: ignore[assignment]

# AST node types imported for type hints in docstrings
# from .ast_nodes import ASTNode, QueryNode, FindNode, TraversalNode, FilterNode
from .query_context import QueryContext
from .ast_builder import ASTBuilder
from .error_handler import ParserError, ErrorHandler

# Import QueryPlan models
try:
    from aiecs.domain.knowledge_graph.models.query_plan import QueryPlan

    QUERY_PLAN_AVAILABLE = True
except ImportError:
    QUERY_PLAN_AVAILABLE = False
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        QueryPlan: Any  # type: ignore[assignment,no-redef]
    else:
        QueryPlan = None  # type: ignore[assignment]


class LogicQueryParser:
    """
    Logic Query DSL Parser

    Parses Logic Query DSL strings into Abstract Syntax Trees (AST).

    This class handles:
    1. Syntax parsing (via Lark)
    2. AST building (via Transformer - to be implemented in Task 2.2)
    3. Two-phase error handling (syntax vs semantic)

    **Thread Safety**: This class is thread-safe. Each parse() call creates
    a fresh QueryContext internally.

    Example:
        ```python
        schema = SchemaManager()
        parser = LogicQueryParser(schema)

        # Parse a query
        result = parser.parse("Find(Person) WHERE age > 30")

        if isinstance(result, list):
            # Errors occurred
            for error in result:
                print(f"Error at line {error.line}: {error.message}")
        else:
            # Success - got AST
            ast = result
            print(f"Parsed: {ast}")
        ```
    """

    def __init__(self, schema: Any = None):
        """
        Initialize the parser

        Args:
            schema: SchemaManager instance for validation (optional for now)

        Raises:
            ImportError: If lark-parser is not installed
        """
        if not LARK_AVAILABLE:
            raise ImportError("lark-parser is required for LogicQueryParser. " "Install with: pip install lark-parser")

        self.schema = schema

        # Load grammar from file
        grammar_path = Path(__file__).parent / "grammar.lark"
        with open(grammar_path, "r") as f:
            grammar_text = f.read()

        # Create Lark parser with LALR algorithm
        self.lark_parser = Lark(
            grammar_text,
            start="query",
            parser="lalr",
            propagate_positions=True,  # Track line/column info
            maybe_placeholders=False,
        )

        # Create AST builder
        self.ast_builder = ASTBuilder()

        # Create error handler
        self.error_handler = ErrorHandler()

    def parse(self, query: str) -> Union[Any, List[ParserError]]:
        """
        Parse a query string into an AST

        This method implements two-phase error handling:
        - Phase 1: Syntax parsing (fatal - stops at first error)
        - Phase 2: Semantic validation (accumulated - returns all errors)

        Args:
            query: Query string to parse

        Returns:
            - AST node if successful
            - List of ParserError if errors occurred

        Example:
            ```python
            result = parser.parse("Find(Person) WHERE age > 30")
            if isinstance(result, list):
                print("Errors:", result)
            else:
                print("AST:", result)
            ```
        """
        # Phase 1: Syntax parsing (fatal errors)
        try:
            parse_tree = self.lark_parser.parse(query)

            # Transform parse tree to AST
            ast = self.ast_builder.transform(parse_tree)

            # Phase 2: Semantic validation (if schema is available)
            if self.schema is not None:
                validation_errors = ast.validate(self.schema)
                if validation_errors:
                    # Convert validation errors to parser errors
                    return [self.error_handler.from_validation_error(err, query) for err in validation_errors]

            return ast

        except (UnexpectedInput, UnexpectedToken, UnexpectedCharacters) as e:
            # Lark syntax error
            return [self.error_handler.from_lark_error(e, query)]
        except LarkError as e:
            # Other Lark errors
            return [self.error_handler.from_lark_error(e, query)]
        except Exception as e:
            # Unexpected errors
            return [
                ParserError(
                    line=1,
                    column=1,
                    message=f"Unexpected error: {str(e)}",
                    phase="syntax",
                )
            ]

    def parse_to_query_plan(self, query: str) -> Any:
        """
        Parse query string and convert to QueryPlan

        This is the main entry point for parsing and converting queries to executable plans.
        It performs:
        1. Syntax parsing (Lark)
        2. AST building (Transformer)
        3. Semantic validation (if schema available)
        4. QueryPlan conversion

        Args:
            query: Query string in Logic Query DSL

        Returns:
            QueryPlan object if successful, or List[ParserError] if errors occurred

        Example:
            ```python
            parser = LogicQueryParser(schema=schema_manager)
            result = parser.parse_to_query_plan("Find(Person) WHERE age > 30")

            if isinstance(result, list):
                # Errors occurred
                for error in result:
                    print(f"Error at line {error.line}: {error.message}")
            else:
                # Success - result is a QueryPlan
                for step in result.steps:
                    print(f"Step {step.step_id}: {step.description}")
            ```
        """
        if not QUERY_PLAN_AVAILABLE:
            return [
                ParserError(
                    line=1,
                    column=1,
                    message="QueryPlan models not available. Cannot convert to query plan.",
                    phase="conversion",
                )
            ]

        # Step 1: Parse to AST
        ast_result = self.parse(query)

        # Check for errors
        if isinstance(ast_result, list):
            # Errors occurred during parsing/validation
            return ast_result

        # Step 2: Create fresh QueryContext for this request (thread-safe)
        context = QueryContext(schema=self.schema)

        # Step 3: Convert AST to QueryPlan
        try:
            query_plan = ast_result.to_query_plan(context, original_query=query)
            return query_plan
        except Exception as e:
            # Conversion error
            return [
                ParserError(
                    line=1,
                    column=1,
                    message=f"Failed to convert to query plan: {str(e)}",
                    phase="conversion",
                )
            ]

    def parse_tree_to_string(self, parse_tree: Any) -> str:
        """
        Convert parse tree to string representation

        Args:
            parse_tree: Lark parse tree

        Returns:
            String representation of the parse tree
        """
        if parse_tree is None:
            return "None"
        return parse_tree.pretty()

    # ========================================================================
    # Multi-Query Support (Batch Processing)
    # ========================================================================

    def parse_batch(self, queries: List[str]) -> List[Any]:
        """
        Parse multiple queries in batch

        This method parses multiple queries independently and returns their
        AST representations. Each query is parsed with its own context.

        Args:
            queries: List of query strings to parse

        Returns:
            List of results (QueryNode or List[ParserError] for each query)

        Example:
            ```python
            parser = LogicQueryParser(schema=schema_manager)
            results = parser.parse_batch([
                "Find(Person) WHERE age > 30",
                "Find(Paper) WHERE year == 2023"
            ])

            for i, result in enumerate(results):
                if isinstance(result, list):
                    print(f"Query {i+1} errors: {result}")
                else:
                    print(f"Query {i+1} success: {result}")
            ```
        """
        results = []
        for query in queries:
            result = self.parse(query)
            results.append(result)
        return results

    def parse_batch_to_query_plans(self, queries: List[str]) -> List[Any]:
        """
        Parse multiple queries and convert to QueryPlans in batch

        This method parses multiple queries and converts them to QueryPlan
        objects. Each query is processed independently with its own context.

        Args:
            queries: List of query strings to parse

        Returns:
            List of results (QueryPlan or List[ParserError] for each query)

        Example:
            ```python
            parser = LogicQueryParser(schema=schema_manager)
            plans = parser.parse_batch_to_query_plans([
                "Find(Person) WHERE age > 30",
                "Find(Paper) WHERE year == 2023"
            ])

            for i, plan in enumerate(plans):
                if isinstance(plan, list):
                    print(f"Query {i+1} errors: {plan}")
                else:
                    print(f"Query {i+1} plan: {plan.plan_id}")
            ```
        """
        results = []
        for query in queries:
            result = self.parse_to_query_plan(query)
            results.append(result)
        return results

    def parse_batch_with_ids(self, queries: Dict[str, str]) -> Dict[str, Any]:
        """
        Parse multiple queries with custom IDs

        This method parses multiple queries and returns results keyed by
        custom IDs. Useful for tracking which result corresponds to which query.

        Args:
            queries: Dictionary mapping query IDs to query strings

        Returns:
            Dictionary mapping query IDs to results (QueryNode or List[ParserError])

        Example:
            ```python
            parser = LogicQueryParser(schema=schema_manager)
            results = parser.parse_batch_with_ids({
                "find_people": "Find(Person) WHERE age > 30",
                "find_papers": "Find(Paper) WHERE year == 2023"
            })

            if isinstance(results["find_people"], list):
                print(f"Errors: {results['find_people']}")
            else:
                print(f"Success: {results['find_people']}")
            ```
        """
        results = {}
        for query_id, query in queries.items():
            result = self.parse(query)
            results[query_id] = result
        return results


# Cached parser instance for performance
@lru_cache(maxsize=1)
def get_cached_parser(schema_id: Optional[int] = None) -> LogicQueryParser:
    """
    Get a cached parser instance

    This is an optional optimization for repeated parsing.

    Args:
        schema_id: Optional schema identifier for cache key

    Returns:
        Cached LogicQueryParser instance

    Note:
        This is optional (Task 2.1.6). The cache is based on schema_id.
        If schema changes, use a different schema_id to get a new parser.
    """
    return LogicQueryParser(schema=None)
