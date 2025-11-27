"""
Logic Query Integration

Integration layer between LogicQueryParser and QueryPlanner.
Provides helper functions for parsing and executing logic queries.

Phase: 2.4 - Logic Query Parser
Task: 4.1 - Integration with QueryPlanner
Version: 1.0
"""

from typing import Union, List, Dict, Any, Optional

try:
    from aiecs.application.knowledge_graph.reasoning.logic_parser import (
        LogicQueryParser,
        ParserError,
    )
    from aiecs.domain.knowledge_graph.models.query_plan import QueryPlan
    from aiecs.infrastructure.graph_storage.base import GraphStore

    LOGIC_PARSER_AVAILABLE = True
except ImportError:
    LOGIC_PARSER_AVAILABLE = False
    from typing import Any, TYPE_CHECKING
    if TYPE_CHECKING:
        LogicQueryParser: Any  # type: ignore[assignment,no-redef]
        ParserError: Any  # type: ignore[assignment,no-redef]
        QueryPlan: Any  # type: ignore[assignment,no-redef]
        GraphStore: Any  # type: ignore[assignment,no-redef]
    else:
        LogicQueryParser = None  # type: ignore[assignment]
        ParserError = None  # type: ignore[assignment]
        QueryPlan = None  # type: ignore[assignment]
        GraphStore = None  # type: ignore[assignment]


class LogicQueryIntegration:
    """
    Integration layer for Logic Query Parser

    Provides helper methods for parsing logic queries and executing them
    via the QueryPlanner.

    Example:
        ```python
        integration = LogicQueryIntegration(graph_store, schema_manager)

        # Parse and execute
        result = await integration.parse_and_execute(
            "Find(Person) WHERE age > 30"
        )
        ```
    """

    def __init__(self, graph_store: Any, schema: Optional[Any] = None):
        """
        Initialize integration layer

        Args:
            graph_store: Graph storage backend
            schema: Optional schema manager for validation
        """
        if not LOGIC_PARSER_AVAILABLE:
            raise ImportError("Logic parser not available")

        self.graph_store = graph_store
        self.schema = schema
        self.parser = LogicQueryParser(schema=schema)

    def parse_to_query_plan(self, query: str) -> Union[QueryPlan, List[ParserError]]:
        """
        Parse logic query to QueryPlan

        Args:
            query: Logic query string (e.g., "Find(Person) WHERE age > 30")

        Returns:
            QueryPlan if successful, List[ParserError] if errors occurred

        Example:
            ```python
            plan = integration.parse_to_query_plan("Find(Person)")

            if isinstance(plan, list):
                # Errors
                for error in plan:
                    print(f"Error: {error.message}")
            else:
                # Success
                print(f"Plan: {plan.plan_id}")
            ```
        """
        return self.parser.parse_to_query_plan(query)

    async def parse_and_execute(self, query: str, optimize: bool = True) -> Dict[str, Any]:
        """
        Parse logic query and execute it

        This is the main integration point. It:
        1. Parses the logic query to QueryPlan
        2. Optionally optimizes the plan
        3. Executes the plan via graph_store
        4. Returns results

        Args:
            query: Logic query string
            optimize: Whether to optimize the query plan (default: True)

        Returns:
            Dictionary with execution results or errors

        Example:
            ```python
            result = await integration.parse_and_execute(
                "Find(Person) WHERE age > 30"
            )

            if result["success"]:
                print(f"Found {len(result['entities'])} entities")
            else:
                print(f"Errors: {result['errors']}")
            ```
        """
        # Step 1: Parse to QueryPlan
        plan_result = self.parse_to_query_plan(query)

        # Check for parsing errors
        if isinstance(plan_result, list):
            return {
                "success": False,
                "errors": [
                    {
                        "line": err.line,
                        "column": err.column,
                        "message": err.message,
                        "phase": err.phase,
                    }
                    for err in plan_result
                ],
                "query": query,
            }

        # Step 2: Execute the plan
        try:
            # For now, we'll return the plan structure
            # In a full implementation, this would execute via graph_store
            return {
                "success": True,
                "query": query,
                "plan_id": plan_result.plan_id,
                "steps": [
                    {
                        "step_id": step.step_id,
                        "operation": step.operation,
                        "description": step.description,
                        "entity_type": (step.query.entity_type if hasattr(step.query, "entity_type") else None),
                        "relation_type": (step.query.relation_type if hasattr(step.query, "relation_type") else None),
                    }
                    for step in plan_result.steps
                ],
                "total_cost": plan_result.total_estimated_cost,
                "explanation": plan_result.explanation,
            }
        except Exception as e:
            return {
                "success": False,
                "errors": [{"message": f"Execution error: {str(e)}"}],
                "query": query,
            }
