"""
Query Plan Domain Models

Models for query planning, decomposition, and optimization.
"""

from typing import Any, List, Dict, Set
from enum import Enum
from pydantic import BaseModel, Field
from aiecs.domain.knowledge_graph.models.query import GraphQuery


class QueryOperation(str, Enum):
    """Types of query operations"""

    ENTITY_LOOKUP = "entity_lookup"
    VECTOR_SEARCH = "vector_search"
    TRAVERSAL = "traversal"
    FILTER = "filter"
    JOIN = "join"
    AGGREGATE = "aggregate"
    RANK = "rank"


class QueryStep(BaseModel):
    """
    A single step in a query execution plan

    Represents one operation in a multi-step query plan.

    Attributes:
        step_id: Unique identifier for this step
        operation: Type of operation to perform
        query: Graph query specification for this step
        depends_on: List of step IDs that must complete before this step
        description: Human-readable description of what this step does
        estimated_cost: Estimated computational cost (0-1, higher = more expensive)

    Example:
        ```python
        step = QueryStep(
            step_id="step_1",
            operation=QueryOperation.VECTOR_SEARCH,
            query=GraphQuery(
                query_type=QueryType.VECTOR_SEARCH,
                embedding=[0.1, 0.2, ...],
                max_results=10
            ),
            description="Find semantically similar entities"
        )
        ```
    """

    step_id: str = Field(..., description="Unique identifier for this step")

    operation: QueryOperation = Field(..., description="Type of operation to perform")

    query: GraphQuery = Field(..., description="Graph query specification for this step")

    depends_on: List[str] = Field(
        default_factory=list,
        description="List of step IDs that must complete before this step",
    )

    description: str = Field(..., description="Human-readable description of what this step does")

    estimated_cost: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Estimated computational cost (0-1, higher = more expensive)",
    )

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata for this step")


class QueryPlan(BaseModel):
    """
    Query Execution Plan

    Represents a structured plan for executing a complex query as a series of steps.

    Attributes:
        plan_id: Unique identifier for this plan
        original_query: The original natural language or complex query
        steps: List of query steps to execute in order
        total_estimated_cost: Total estimated cost of executing this plan
        optimized: Whether this plan has been optimized
        explanation: Human-readable explanation of the plan

    Example:
        ```python
        plan = QueryPlan(
            plan_id="plan_001",
            original_query="Who works at companies that Alice knows people at?",
            steps=[
                QueryStep(step_id="step_1", ...),  # Find Alice
                QueryStep(step_id="step_2", ...),  # Find people Alice knows
                QueryStep(step_id="step_3", ...)   # Find their companies
            ],
            explanation="Multi-hop query to find companies through social connections"
        )
        ```
    """

    plan_id: str = Field(..., description="Unique identifier for this plan")

    original_query: str = Field(..., description="The original natural language or complex query")

    steps: List[QueryStep] = Field(..., description="List of query steps to execute in order")

    total_estimated_cost: float = Field(default=0.0, description="Total estimated cost of executing this plan")

    optimized: bool = Field(default=False, description="Whether this plan has been optimized")

    explanation: str = Field(default="", description="Human-readable explanation of the plan")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata for this plan")

    def calculate_total_cost(self) -> float:
        """Calculate total estimated cost from all steps"""
        return sum(step.estimated_cost for step in self.steps)

    def get_executable_steps(self, completed_step_ids: set[str]) -> List[QueryStep]:
        """
        Get steps that can be executed given completed steps

        Args:
            completed_step_ids: Set of step IDs that have been completed

        Returns:
            List of steps whose dependencies are all satisfied
        """
        executable = []
        for step in self.steps:
            if step.step_id in completed_step_ids:
                continue
            if all(dep in completed_step_ids for dep in step.depends_on):
                executable.append(step)
        return executable

    def get_execution_order(self) -> List[List[str]]:
        """
        Get optimal execution order for steps

        Returns:
            List of lists, where each inner list contains step IDs that can run in parallel

        Example:
            [[step_1], [step_2, step_3], [step_4]]
            - step_1 runs first
            - step_2 and step_3 can run in parallel after step_1
            - step_4 runs after both step_2 and step_3 complete
        """
        completed: Set[str] = set()
        execution_order: List[List[str]] = []

        while len(completed) < len(self.steps):
            # Get all steps that can run now
            current_batch = []
            for step in self.steps:
                if step.step_id not in completed:
                    if all(dep in completed for dep in step.depends_on):
                        current_batch.append(step.step_id)

            if not current_batch:
                # Should not happen if dependencies are valid
                break

            execution_order.append(current_batch)
            completed.update(current_batch)

        return execution_order


class OptimizationStrategy(str, Enum):
    """Query optimization strategies"""

    MINIMIZE_COST = "minimize_cost"  # Reorder to minimize total cost
    MINIMIZE_LATENCY = "minimize_latency"  # Maximize parallelization
    BALANCED = "balanced"  # Balance cost and latency
