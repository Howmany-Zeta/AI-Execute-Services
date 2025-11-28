"""
Query Planner

Translates natural language queries to structured graph query plans.
Decomposes complex queries into executable steps and optimizes execution order.
"""

import uuid
import re
from typing import Optional, List, Dict, Any, Set, Union
from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.domain.knowledge_graph.models.query import GraphQuery, QueryType
from aiecs.domain.knowledge_graph.models.query_plan import (
    QueryPlan,
    QueryStep,
    QueryOperation,
    OptimizationStrategy,
)
from aiecs.infrastructure.graph_storage.query_optimizer import (
    QueryOptimizer,
    QueryStatisticsCollector,
)

# Import LogicQueryParser for DSL support
try:
    from aiecs.application.knowledge_graph.reasoning.logic_parser import (
        LogicQueryParser,
        ParserError,
    )

    LOGIC_PARSER_AVAILABLE = True
except ImportError:
    LOGIC_PARSER_AVAILABLE = False
    from typing import Any, TYPE_CHECKING
    if TYPE_CHECKING:
        LogicQueryParser: Any  # type: ignore[assignment,no-redef]
        ParserError: Any  # type: ignore[assignment,no-redef]
    else:
        LogicQueryParser = None  # type: ignore[assignment]
        ParserError = None  # type: ignore[assignment]


class QueryPlanner:
    """
    Query Planning Engine

    Translates natural language queries into structured, optimized execution plans.

    Features:
    - Natural language to graph query translation
    - Query decomposition (complex queries → multiple steps)
    - Query optimization (reorder operations for efficiency)
    - Cost estimation

    Example::

        planner = QueryPlanner(graph_store)

        # Plan a complex query
        plan = planner.plan_query(
            "Who works at companies that Alice knows people at?"
        )

        # Optimize the plan
        optimized_plan = planner.optimize_plan(
            plan,
            strategy=OptimizationStrategy.MINIMIZE_COST
        )
    """

    def __init__(
        self,
        graph_store: GraphStore,
        enable_advanced_optimization: bool = True,
        schema: Optional[Any] = None,
    ):
        """
        Initialize query planner

        Args:
            graph_store: Graph storage backend for queries
            enable_advanced_optimization: Enable advanced query optimization (default: True)
            schema: Optional schema manager for logic query validation
        """
        self.graph_store = graph_store
        self.schema = schema

        # Pattern templates for query understanding
        self.query_patterns = self._initialize_query_patterns()

        # Advanced query optimizer
        self._enable_advanced_optimization = enable_advanced_optimization
        # Type annotations for optional attributes
        self._optimizer: Optional[QueryOptimizer]
        self._statistics_collector: Optional[QueryStatisticsCollector]
        self._logic_parser: Optional[LogicQueryParser]
        
        if enable_advanced_optimization:
            # Collect statistics from graph store
            collector = QueryStatisticsCollector()
            statistics = collector.collect_from_graph_store(graph_store)

            # Initialize optimizer
            self._optimizer = QueryOptimizer(statistics=statistics)
            self._statistics_collector = collector
        else:
            self._optimizer = None
            self._statistics_collector = None

        # Logic query parser (if available)
        if LOGIC_PARSER_AVAILABLE and schema is not None:
            self._logic_parser = LogicQueryParser(schema=schema)  # type: ignore[assignment]
        else:
            self._logic_parser = None

    def _initialize_query_patterns(self) -> List[Dict[str, Any]]:
        """Initialize query pattern matchers"""
        return [
            {
                "pattern": r"find (.*?) with (.*?) = (['\"]?.+?['\"]?)",
                "type": "entity_lookup_by_property",
                "operations": ["filter"],
            },
            {
                "pattern": r"who (works at|is employed by) (.*?)",
                "type": "relation_traversal",
                "operations": ["entity_lookup", "traversal"],
            },
            {
                "pattern": r"what (companies|organizations) does (.*?) know people at",
                "type": "multi_hop_query",
                "operations": ["entity_lookup", "traversal", "traversal"],
            },
            {
                "pattern": r"(similar|related) to (.*?)",
                "type": "vector_search",
                "operations": ["vector_search"],
            },
            {
                "pattern": r"path from (.*?) to (.*?)",
                "type": "path_finding",
                "operations": ["path_finding"],
            },
            {
                "pattern": r"neighbors of (.*?)",
                "type": "neighbor_query",
                "operations": ["entity_lookup", "traversal"],
            },
        ]

    def plan_query(
        self,
        natural_language_query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> QueryPlan:
        """
        Create an execution plan from natural language query

        Args:
            natural_language_query: Natural language query string
            context: Optional context (e.g., embeddings, entity IDs)

        Returns:
            Query execution plan

        Example::

            plan = planner.plan_query(
                "Find papers similar to 'Deep Learning' and their authors"
            )
        """
        context = context or {}
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"

        # Analyze query structure
        query_info = self._analyze_query(natural_language_query)

        # Decompose into steps
        steps = self._decompose_query(natural_language_query, query_info, context)

        # Create plan
        plan = QueryPlan(
            plan_id=plan_id,
            original_query=natural_language_query,
            steps=steps,
            explanation=self._generate_explanation(steps),
            metadata={"query_info": query_info},
        )

        # Calculate total cost
        plan.total_estimated_cost = plan.calculate_total_cost()

        return plan

    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze query to determine type and complexity

        Args:
            query: Natural language query

        Returns:
            Query analysis information
        """
        query_lower = query.lower()

        # Match against known patterns
        matched_pattern = None
        for pattern_info in self.query_patterns:
            if re.search(pattern_info["pattern"], query_lower):
                matched_pattern = pattern_info
                break

        # Determine complexity
        is_multi_hop = any(
            keyword in query_lower
            for keyword in [
                "who works at",
                "people at",
                "friends of",
                "colleagues",
                "through",
                "connected to",
                "related through",
            ]
        )

        has_vector_search = any(keyword in query_lower for keyword in ["similar", "related", "like", "semantically"])

        has_path_finding = any(keyword in query_lower for keyword in ["path", "route", "connection", "how to get"])

        return {
            "matched_pattern": matched_pattern,
            "is_multi_hop": is_multi_hop,
            "has_vector_search": has_vector_search,
            "has_path_finding": has_path_finding,
            "complexity": self._estimate_complexity(query_lower),
        }

    def _estimate_complexity(self, query: str) -> str:
        """Estimate query complexity"""
        hop_indicators = query.count("who") + query.count("what") + query.count("which")

        if hop_indicators > 2 or "through" in query:
            return "high"
        elif hop_indicators > 0 or any(k in query for k in ["find", "get", "show"]):
            return "medium"
        else:
            return "low"

    def _decompose_query(self, query: str, query_info: Dict[str, Any], context: Dict[str, Any]) -> List[QueryStep]:
        """
        Decompose query into executable steps

        Args:
            query: Natural language query
            query_info: Query analysis information
            context: Query context

        Returns:
            List of query steps
        """
        steps = []

        # Use matched pattern if available
        if query_info["matched_pattern"]:
            steps = self._create_steps_from_pattern(query, query_info["matched_pattern"], context)
        else:
            # Fall back to generic decomposition
            steps = self._create_generic_steps(query, query_info, context)

        return steps

    def _create_steps_from_pattern(self, query: str, pattern_info: Dict[str, Any], context: Dict[str, Any]) -> List[QueryStep]:
        """Create steps based on matched pattern"""
        steps = []
        query_type = pattern_info["type"]

        if query_type == "entity_lookup_by_property":
            # Single step: filter entities by property
            steps.append(
                QueryStep(
                    step_id="step_1",
                    operation=QueryOperation.FILTER,
                    query=GraphQuery(
                        query_type=QueryType.CUSTOM,
                        properties=context.get("properties", {}),
                        max_results=context.get("max_results", 10),
                    ),
                    description="Filter entities by properties",
                    estimated_cost=0.3,
                )
            )

        elif query_type == "relation_traversal":
            # Two steps: lookup entity, traverse relations
            steps.append(
                QueryStep(
                    step_id="step_1",
                    operation=QueryOperation.ENTITY_LOOKUP,
                    query=GraphQuery(
                        query_type=QueryType.ENTITY_LOOKUP,
                        entity_id=context.get("entity_id"),
                        max_results=1,
                    ),
                    description="Look up starting entity",
                    estimated_cost=0.2,
                )
            )

            steps.append(
                QueryStep(
                    step_id="step_2",
                    operation=QueryOperation.TRAVERSAL,
                    query=GraphQuery(
                        query_type=QueryType.TRAVERSAL,
                        relation_type=context.get("relation_type"),
                        max_depth=context.get("max_depth", 1),
                        max_results=context.get("max_results", 10),
                    ),
                    depends_on=["step_1"],
                    description="Traverse relations from starting entity",
                    estimated_cost=0.5,
                )
            )

        elif query_type == "multi_hop_query":
            # Multiple hops
            steps = self._create_multi_hop_steps(query, context)

        elif query_type == "vector_search":
            # Single step: vector similarity search
            steps.append(
                QueryStep(
                    step_id="step_1",
                    operation=QueryOperation.VECTOR_SEARCH,
                    query=GraphQuery(
                        query_type=QueryType.VECTOR_SEARCH,
                        embedding=context.get("query_embedding"),
                        entity_type=context.get("entity_type"),
                        max_results=context.get("max_results", 10),
                        score_threshold=context.get("score_threshold", 0.7),
                    ),
                    description="Find semantically similar entities",
                    estimated_cost=0.4,
                )
            )

        elif query_type == "path_finding":
            # Single step: find path between entities
            steps.append(
                QueryStep(
                    step_id="step_1",
                    operation=QueryOperation.TRAVERSAL,
                    query=GraphQuery(
                        query_type=QueryType.PATH_FINDING,
                        source_entity_id=context.get("source_id"),
                        target_entity_id=context.get("target_id"),
                        max_depth=context.get("max_depth", 5),
                        max_results=context.get("max_results", 10),
                    ),
                    description="Find paths between entities",
                    estimated_cost=0.7,
                )
            )

        elif query_type == "neighbor_query":
            # Two steps: lookup + get neighbors
            steps.append(
                QueryStep(
                    step_id="step_1",
                    operation=QueryOperation.ENTITY_LOOKUP,
                    query=GraphQuery(
                        query_type=QueryType.ENTITY_LOOKUP,
                        entity_id=context.get("entity_id"),
                        max_results=1,
                    ),
                    description="Look up central entity",
                    estimated_cost=0.2,
                )
            )

            steps.append(
                QueryStep(
                    step_id="step_2",
                    operation=QueryOperation.TRAVERSAL,
                    query=GraphQuery(
                        query_type=QueryType.TRAVERSAL,
                        max_depth=1,
                        max_results=context.get("max_results", 20),
                    ),
                    depends_on=["step_1"],
                    description="Get neighboring entities",
                    estimated_cost=0.4,
                )
            )

        return steps

    def _create_multi_hop_steps(self, query: str, context: Dict[str, Any]) -> List[QueryStep]:
        """Create steps for multi-hop query"""
        steps = []
        num_hops = context.get("num_hops", 2)

        # Step 1: Find starting entity
        steps.append(
            QueryStep(
                step_id="step_1",
                operation=QueryOperation.ENTITY_LOOKUP,
                query=GraphQuery(
                    query_type=QueryType.ENTITY_LOOKUP,
                    entity_id=context.get("start_entity_id"),
                    max_results=1,
                ),
                description="Find starting entity",
                estimated_cost=0.2,
            )
        )

        # Create hop steps
        for i in range(num_hops):
            hop_num = i + 1
            step_id = f"step_{hop_num + 1}"
            depends_on = [f"step_{hop_num}"]

            steps.append(
                QueryStep(
                    step_id=step_id,
                    operation=QueryOperation.TRAVERSAL,
                    query=GraphQuery(
                        query_type=QueryType.TRAVERSAL,
                        relation_type=context.get(f"hop{hop_num}_relation"),
                        max_depth=1,
                        max_results=context.get("max_results", 20),
                    ),
                    depends_on=depends_on,
                    description=f"Hop {hop_num}: Traverse to next level",
                    estimated_cost=0.4 + (0.1 * i),  # Cost increases with depth
                )
            )

        return steps

    def _create_generic_steps(self, query: str, query_info: Dict[str, Any], context: Dict[str, Any]) -> List[QueryStep]:
        """Create generic steps when no pattern matches"""
        steps = []

        # Priority 1: If start_entity_id is provided, use traversal
        if context.get("start_entity_id"):
            # Step 1: Lookup starting entity
            steps.append(
                QueryStep(
                    step_id="step_1",
                    operation=QueryOperation.ENTITY_LOOKUP,
                    query=GraphQuery(
                        query_type=QueryType.ENTITY_LOOKUP,
                        entity_id=context.get("start_entity_id"),
                        max_results=1,
                    ),
                    description="Look up starting entity",
                    estimated_cost=0.2,
                )
            )

            # Step 2: Traverse from starting entity
            target_id = context.get("target_entity_id")
            if target_id:
                # Path finding if target is specified
                steps.append(
                    QueryStep(
                        step_id="step_2",
                        operation=QueryOperation.TRAVERSAL,
                        query=GraphQuery(
                            query_type=QueryType.PATH_FINDING,
                            source_entity_id=context.get("start_entity_id"),
                            target_entity_id=target_id,
                            max_depth=context.get("max_hops", 3),
                            max_results=context.get("max_results", 10),
                        ),
                        depends_on=["step_1"],
                        description="Find paths from start to target entity",
                        estimated_cost=0.6,
                    )
                )
            else:
                # General traversal if no target
                steps.append(
                    QueryStep(
                        step_id="step_2",
                        operation=QueryOperation.TRAVERSAL,
                        query=GraphQuery(
                            query_type=QueryType.TRAVERSAL,
                            entity_id=context.get("start_entity_id"),
                            relation_type=(context.get("relation_types", [None])[0] if context.get("relation_types") else None),
                            max_depth=context.get("max_hops", 3),
                            max_results=context.get("max_results", 10),
                        ),
                        depends_on=["step_1"],
                        description="Traverse from starting entity",
                        estimated_cost=0.5,
                    )
                )

        # Priority 2: If query_embedding is provided, use vector search
        elif context.get("query_embedding"):
            steps.append(
                QueryStep(
                    step_id="step_1",
                    operation=QueryOperation.VECTOR_SEARCH,
                    query=GraphQuery(
                        query_type=QueryType.VECTOR_SEARCH,
                        embedding=context.get("query_embedding"),
                        entity_type=context.get("entity_type"),
                        max_results=context.get("max_results", 10),
                        score_threshold=context.get("score_threshold", 0.5),
                    ),
                    description="Search for relevant entities using vector similarity",
                    estimated_cost=0.5,
                )
            )

        # Priority 3: Default fallback - entity lookup by type if entity_type
        # is provided
        elif context.get("entity_type"):
            steps.append(
                QueryStep(
                    step_id="step_1",
                    operation=QueryOperation.FILTER,
                    query=GraphQuery(
                        query_type=QueryType.ENTITY_LOOKUP,
                        entity_type=context.get("entity_type"),
                        max_results=context.get("max_results", 10),
                    ),
                    description=f"Filter entities by type: {context.get('entity_type')}",
                    estimated_cost=0.3,
                )
            )

        # Priority 4: Last resort - simple vector search (may not work without
        # embeddings)
        else:
            steps.append(
                QueryStep(
                    step_id="step_1",
                    operation=QueryOperation.VECTOR_SEARCH,
                    query=GraphQuery(
                        query_type=QueryType.VECTOR_SEARCH,
                        embedding=None,  # Will need to be generated
                        max_results=context.get("max_results", 10),
                        score_threshold=0.5,
                    ),
                    description="Search for relevant entities (fallback - may not work without embeddings)",
                    estimated_cost=0.5,
                )
            )

        return steps

    def _generate_explanation(self, steps: List[QueryStep]) -> str:
        """Generate human-readable explanation of plan"""
        if not steps:
            return "No steps in plan"

        if len(steps) == 1:
            return f"Single-step query: {steps[0].description}"

        parts = [f"Multi-step query with {len(steps)} steps:"]
        for i, step in enumerate(steps, 1):
            parts.append(f"{i}. {step.description}")

        return "\n".join(parts)

    def optimize_plan(
        self,
        plan: QueryPlan,
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
    ) -> QueryPlan:
        """
        Optimize query execution plan

        Args:
            plan: Original query plan
            strategy: Optimization strategy

        Returns:
            Optimized query plan

        Example::

            optimized = planner.optimize_plan(
                plan,
                strategy=OptimizationStrategy.MINIMIZE_COST
            )
        """
        if plan.optimized:
            return plan  # Already optimized

        # Use advanced optimizer if enabled
        if self._enable_advanced_optimization and self._optimizer:
            result = self._optimizer.optimize(plan)
            return result.optimized_plan

        # Fall back to basic optimization
        optimized_steps = list(plan.steps)

        if strategy == OptimizationStrategy.MINIMIZE_COST:
            optimized_steps = self._optimize_for_cost(optimized_steps)
        elif strategy == OptimizationStrategy.MINIMIZE_LATENCY:
            optimized_steps = self._optimize_for_latency(optimized_steps)
        else:  # BALANCED
            optimized_steps = self._optimize_balanced(optimized_steps)

        # Create optimized plan
        optimized_plan = QueryPlan(
            plan_id=plan.plan_id + "_opt",
            original_query=plan.original_query,
            steps=optimized_steps,
            optimized=True,
            explanation=plan.explanation + "\n(Optimized)",
            metadata=plan.metadata,
        )

        optimized_plan.total_estimated_cost = optimized_plan.calculate_total_cost()

        return optimized_plan

    def _optimize_for_cost(self, steps: List[QueryStep]) -> List[QueryStep]:
        """
        Optimize to minimize total cost

        Strategy: Execute cheaper operations first when possible
        """
        # Group steps by dependency level
        levels = self._get_dependency_levels(steps)

        optimized = []
        for level_steps in levels:
            # Sort by cost (ascending) within each level
            sorted_level = sorted(level_steps, key=lambda s: s.estimated_cost)
            optimized.extend(sorted_level)

        return optimized

    def _optimize_for_latency(self, steps: List[QueryStep]) -> List[QueryStep]:
        """
        Optimize to minimize latency

        Strategy: Maximize parallelization
        """
        # Already maximized in get_execution_order()
        # Just return original order
        return steps

    def _optimize_balanced(self, steps: List[QueryStep]) -> List[QueryStep]:
        """
        Balanced optimization

        Strategy: Balance cost and latency
        """
        levels = self._get_dependency_levels(steps)

        optimized = []
        for level_steps in levels:
            # Sort by cost but not too aggressively
            # Keep expensive operations that can run in parallel
            sorted_level = sorted(
                level_steps,
                key=lambda s: (s.estimated_cost > 0.7, s.estimated_cost),
            )
            optimized.extend(sorted_level)

        return optimized

    def _get_dependency_levels(self, steps: List[QueryStep]) -> List[List[QueryStep]]:
        """
        Group steps by dependency level

        Returns:
            List of lists, each containing steps at the same dependency level
        """
        # step_map = {step.step_id: step for step in steps}  # Reserved for
        # future use
        levels: List[List[QueryStep]] = []
        processed: Set[str] = set()

        while len(processed) < len(steps):
            current_level = []
            for step in steps:
                if step.step_id in processed:
                    continue
                # Check if all dependencies are processed
                if all(dep in processed for dep in step.depends_on):
                    current_level.append(step)

            if not current_level:
                break  # Should not happen with valid dependencies

            levels.append(current_level)
            processed.update(step.step_id for step in current_level)

        return levels

    def translate_to_graph_query(
        self,
        natural_language_query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> GraphQuery:
        """
        Translate natural language to a single graph query

        For simple queries that don't need decomposition.

        Args:
            natural_language_query: Natural language query
            context: Query context (embeddings, entity IDs, etc.)

        Returns:
            Single graph query

        Example::

            query = planner.translate_to_graph_query(
                "Find entities similar to X",
                context={"query_embedding": [0.1, 0.2, ...]}
            )
        """
        context = context or {}
        query_lower = natural_language_query.lower()

        # Determine query type
        if "similar" in query_lower or "related" in query_lower:
            return GraphQuery(
                query_type=QueryType.VECTOR_SEARCH,
                embedding=context.get("query_embedding"),
                entity_type=context.get("entity_type"),
                max_results=context.get("max_results", 10),
                score_threshold=context.get("score_threshold", 0.7),
            )

        elif "path" in query_lower:
            return GraphQuery(
                query_type=QueryType.PATH_FINDING,
                source_entity_id=context.get("source_id"),
                target_entity_id=context.get("target_id"),
                max_depth=context.get("max_depth", 5),
                max_results=context.get("max_results", 10),
            )

        elif "neighbor" in query_lower or "connected to" in query_lower:
            return GraphQuery(
                query_type=QueryType.TRAVERSAL,
                entity_id=context.get("entity_id"),
                relation_type=context.get("relation_type"),
                max_depth=1,
                max_results=context.get("max_results", 20),
            )

        else:
            # Default to entity lookup
            return GraphQuery(
                query_type=QueryType.ENTITY_LOOKUP,
                entity_id=context.get("entity_id"),
                entity_type=context.get("entity_type"),
                properties=context.get("properties", {}),
                max_results=context.get("max_results", 10),
            )

    # Advanced Optimization Methods

    def update_statistics(self) -> None:
        """
        Update query statistics from graph store

        Call this periodically to keep optimizer statistics up-to-date
        """
        if self._enable_advanced_optimization and self._statistics_collector and self._optimizer:
            statistics = self._statistics_collector.collect_from_graph_store(self.graph_store)
            self._optimizer.update_statistics(statistics)

    def record_execution_time(self, execution_time_ms: float) -> None:
        """
        Record query execution time for statistics

        Args:
            execution_time_ms: Execution time in milliseconds
        """
        if self._statistics_collector:
            self._statistics_collector.record_execution_time(execution_time_ms)

    def get_optimizer_stats(self) -> Dict[str, Any]:
        """
        Get optimizer statistics

        Returns:
            Dictionary with optimizer statistics
        """
        if not self._enable_advanced_optimization or not self._optimizer:
            return {"enabled": False}

        return {
            "enabled": True,
            "optimizations_performed": self._optimizer.get_optimization_count(),
            "avg_execution_time_ms": (self._statistics_collector.get_average_execution_time() if self._statistics_collector else 0.0),
            "p95_execution_time_ms": (self._statistics_collector.get_execution_percentile(0.95) if self._statistics_collector else 0.0),
            "entity_count": self._optimizer.statistics.entity_count,
            "relation_count": self._optimizer.statistics.relation_count,
            "avg_degree": self._optimizer.statistics.avg_degree,
        }

    # ========================================================================
    # Logic Query Support
    # ========================================================================

    def plan_logic_query(self, logic_query: str) -> Union[QueryPlan, List[Any]]:
        """
        Create execution plan from logic query DSL

        This method parses a logic query (e.g., "Find(Person) WHERE age > 30")
        and converts it directly to a QueryPlan.

        Args:
            logic_query: Logic query string in DSL format

        Returns:
            QueryPlan if successful, List[ParserError] if errors occurred

        Example::

            plan = planner.plan_logic_query("Find(Person) WHERE age > 30")

            if isinstance(plan, list):
                # Parsing errors
                for error in plan:
                    print(f"Error at line {error.line}: {error.message}")
            else:
                # Success - execute the plan
                result = await graph_store.execute_plan(plan)
        """
        if not LOGIC_PARSER_AVAILABLE:
            raise ImportError("Logic parser not available. Install lark-parser.")

        if self._logic_parser is None:
            raise ValueError("Logic parser not initialized. Provide schema to QueryPlanner.")

        # Parse logic query to QueryPlan
        return self._logic_parser.parse_to_query_plan(logic_query)

    def supports_logic_queries(self) -> bool:
        """
        Check if logic query support is available

        Returns:
            True if logic queries are supported, False otherwise
        """
        return LOGIC_PARSER_AVAILABLE and self._logic_parser is not None
