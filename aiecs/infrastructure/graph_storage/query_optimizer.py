"""
Query Optimizer

Advanced query optimization for knowledge graph queries.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from aiecs.domain.knowledge_graph.models.query_plan import QueryPlan, QueryStep
from aiecs.domain.knowledge_graph.models.query import QueryType

logger = logging.getLogger(__name__)


class OptimizationRule(str, Enum):
    """Query optimization rules"""

    PREDICATE_PUSHDOWN = "predicate_pushdown"
    JOIN_REORDERING = "join_reordering"
    REDUNDANT_ELIMINATION = "redundant_elimination"
    FILTER_EARLY = "filter_early"
    COST_BASED = "cost_based"


@dataclass
class QueryStatistics:
    """
    Query execution statistics for cost estimation

    Attributes:
        entity_count: Estimated number of entities in graph
        relation_count: Estimated number of relations in graph
        avg_degree: Average node degree (connections per entity)
        entity_type_counts: Count of entities per type
        relation_type_counts: Count of relations per type
    """

    entity_count: int = 1000
    relation_count: int = 5000
    avg_degree: float = 5.0
    entity_type_counts: Dict[str, int] = field(default_factory=dict)
    relation_type_counts: Dict[str, int] = field(default_factory=dict)

    def get_selectivity(self, entity_type: Optional[str] = None) -> float:
        """
        Estimate selectivity (fraction of entities matching filter)

        Args:
            entity_type: Entity type filter

        Returns:
            Selectivity estimate (0.0-1.0)
        """
        if entity_type and entity_type in self.entity_type_counts:
            return self.entity_type_counts[entity_type] / max(self.entity_count, 1)
        return 1.0  # No filter = all entities


@dataclass
class OptimizationResult:
    """
    Result of query optimization

    Attributes:
        original_plan: Original query plan
        optimized_plan: Optimized query plan
        rules_applied: List of optimization rules applied
        estimated_cost_reduction: Estimated cost reduction (0.0-1.0)
        explanation: Human-readable explanation of optimizations
    """

    original_plan: QueryPlan
    optimized_plan: QueryPlan
    rules_applied: List[str] = field(default_factory=list)
    estimated_cost_reduction: float = 0.0
    explanation: str = ""


class QueryOptimizer:
    """
    Advanced Query Optimizer

    Optimizes query execution plans using various optimization techniques:
    - Predicate push-down: Move filters earlier in execution
    - Join reordering: Reorder multi-hop queries for efficiency
    - Redundant operation elimination: Remove duplicate operations
    - Cost-based optimization: Choose execution order based on cost estimates

    Example:
        ```python
        optimizer = QueryOptimizer(statistics=stats)

        # Optimize a query plan
        result = optimizer.optimize(plan)

        print(f"Cost reduction: {result.estimated_cost_reduction:.1%}")
        print(f"Rules applied: {result.rules_applied}")
        ```
    """

    def __init__(
        self,
        statistics: Optional[QueryStatistics] = None,
        enable_rules: Optional[List[OptimizationRule]] = None,
    ):
        """
        Initialize query optimizer

        Args:
            statistics: Query statistics for cost estimation
            enable_rules: List of optimization rules to enable (None = all)
        """
        self.statistics = statistics or QueryStatistics()
        self.enable_rules = enable_rules or list(OptimizationRule)
        self._optimization_count = 0

    def optimize(self, plan: QueryPlan) -> OptimizationResult:
        """
        Optimize a query execution plan

        Args:
            plan: Original query plan

        Returns:
            Optimization result with optimized plan
        """
        if plan.optimized:
            logger.debug(f"Plan {plan.plan_id} already optimized")
            return OptimizationResult(
                original_plan=plan,
                optimized_plan=plan,
                explanation="Plan already optimized",
            )

        original_cost = plan.total_estimated_cost
        optimized_steps = list(plan.steps)
        rules_applied = []

        # Apply optimization rules in order
        if OptimizationRule.REDUNDANT_ELIMINATION in self.enable_rules:
            optimized_steps, eliminated = self._eliminate_redundant_operations(optimized_steps)
            if eliminated > 0:
                rules_applied.append(f"redundant_elimination (removed {eliminated} ops)")

        if OptimizationRule.PREDICATE_PUSHDOWN in self.enable_rules:
            optimized_steps, pushed = self._push_down_predicates(optimized_steps)
            if pushed > 0:
                rules_applied.append(f"predicate_pushdown (pushed {pushed} filters)")

        if OptimizationRule.JOIN_REORDERING in self.enable_rules:
            optimized_steps = self._reorder_joins(optimized_steps)
            rules_applied.append("join_reordering")

        if OptimizationRule.COST_BASED in self.enable_rules:
            optimized_steps = self._cost_based_reordering(optimized_steps)
            rules_applied.append("cost_based_reordering")

        # Create optimized plan
        optimized_plan = QueryPlan(
            plan_id=plan.plan_id,
            original_query=plan.original_query,
            steps=optimized_steps,
            optimized=True,
            explanation=plan.explanation,
            metadata=plan.metadata,
        )
        optimized_plan.total_estimated_cost = optimized_plan.calculate_total_cost()

        # Calculate cost reduction
        cost_reduction = 0.0
        if original_cost > 0:
            cost_reduction = (original_cost - optimized_plan.total_estimated_cost) / original_cost

        self._optimization_count += 1

        explanation = self._generate_explanation(plan, optimized_plan, rules_applied, cost_reduction)

        return OptimizationResult(
            original_plan=plan,
            optimized_plan=optimized_plan,
            rules_applied=rules_applied,
            estimated_cost_reduction=cost_reduction,
            explanation=explanation,
        )

    def _eliminate_redundant_operations(self, steps: List[QueryStep]) -> Tuple[List[QueryStep], int]:
        """
        Eliminate redundant operations

        Args:
            steps: Query steps

        Returns:
            Tuple of (optimized steps, number of operations eliminated)
        """
        seen_operations: Dict[str, QueryStep] = {}
        optimized = []
        eliminated = 0

        for step in steps:
            # Create a signature for this operation
            signature = self._get_operation_signature(step)

            if signature in seen_operations:
                # Redundant operation - update dependencies to point to
                # original
                original_step = seen_operations[signature]

                # Update other steps that depend on this redundant step
                for other_step in steps:
                    if step.step_id in other_step.depends_on:
                        # Replace dependency with original step
                        other_step.depends_on = [(original_step.step_id if dep == step.step_id else dep) for dep in other_step.depends_on]

                eliminated += 1
                logger.debug(f"Eliminated redundant operation: {step.step_id} -> {original_step.step_id}")
            else:
                seen_operations[signature] = step
                optimized.append(step)

        return optimized, eliminated

    def _get_operation_signature(self, step: QueryStep) -> str:
        """
        Get a signature for an operation to detect duplicates

        Args:
            step: Query step

        Returns:
            Signature string
        """
        query = step.query
        parts = [
            str(step.operation),
            str(query.query_type),
            str(query.entity_id or ""),
            str(query.entity_type or ""),
            str(query.relation_type or ""),
            str(sorted(query.properties.items()) if query.properties else ""),
        ]
        return "|".join(parts)

    def _push_down_predicates(self, steps: List[QueryStep]) -> Tuple[List[QueryStep], int]:
        """
        Push predicates (filters) earlier in execution

        Strategy: Move property filters to the earliest possible step

        Args:
            steps: Query steps

        Returns:
            Tuple of (optimized steps, number of predicates pushed)
        """
        pushed_count = 0

        # Find filter steps
        for i, step in enumerate(steps):
            if not step.query.properties:
                continue

            # Check if we can push this filter to an earlier step
            for j in range(i):
                earlier_step = steps[j]

                # Can only push to steps this one depends on
                if earlier_step.step_id not in step.depends_on:
                    continue

                # Check if filter is applicable to earlier step
                if self._can_apply_filter(earlier_step, step.query.properties):
                    # Move filter to earlier step
                    earlier_step.query.properties.update(step.query.properties)
                    step.query.properties = {}
                    pushed_count += 1
                    logger.debug(f"Pushed filter from {step.step_id} to {earlier_step.step_id}")
                    break

        return steps, pushed_count

    def _can_apply_filter(self, step: QueryStep, properties: Dict[str, Any]) -> bool:
        """
        Check if a filter can be applied to a step

        Args:
            step: Query step
            properties: Property filters

        Returns:
            True if filter can be applied
        """
        # Can apply filters to entity lookup and vector search
        return step.query.query_type in [
            QueryType.ENTITY_LOOKUP,
            QueryType.VECTOR_SEARCH,
            QueryType.TRAVERSAL,
        ]

    def _reorder_joins(self, steps: List[QueryStep]) -> List[QueryStep]:
        """
        Reorder join operations (multi-hop queries) for efficiency

        Strategy: Execute most selective operations first

        Args:
            steps: Query steps

        Returns:
            Reordered steps
        """
        # Group steps by dependency level
        levels = self._get_dependency_levels(steps)

        reordered = []
        for level_steps in levels:
            # Sort by selectivity (most selective first)
            sorted_level = sorted(level_steps, key=lambda s: self._estimate_selectivity(s))
            reordered.extend(sorted_level)

        return reordered

    def _estimate_selectivity(self, step: QueryStep) -> float:
        """
        Estimate selectivity of a query step (fraction of results returned)

        Lower selectivity = fewer results = should execute first

        Args:
            step: Query step

        Returns:
            Selectivity estimate (0.0-1.0)
        """
        query = step.query
        selectivity = 1.0

        # Entity type filter
        if query.entity_type:
            selectivity *= self.statistics.get_selectivity(query.entity_type)

        # Property filters
        if query.properties:
            # Each property filter reduces selectivity
            selectivity *= 0.5 ** len(query.properties)

        # Score threshold
        if query.score_threshold > 0:
            selectivity *= 1.0 - query.score_threshold

        # Max results limit
        if query.max_results:
            # Estimate based on total entity count
            limit_selectivity = query.max_results / max(self.statistics.entity_count, 1)
            selectivity = min(selectivity, limit_selectivity)

        return selectivity

    def _cost_based_reordering(self, steps: List[QueryStep]) -> List[QueryStep]:
        """
        Reorder steps based on estimated cost

        Strategy: Execute cheaper operations first within each dependency level

        Args:
            steps: Query steps

        Returns:
            Reordered steps
        """
        levels = self._get_dependency_levels(steps)

        reordered = []
        for level_steps in levels:
            # Sort by estimated cost (ascending)
            sorted_level = sorted(level_steps, key=lambda s: self._estimate_step_cost(s))
            reordered.extend(sorted_level)

        return reordered

    def _estimate_step_cost(self, step: QueryStep) -> float:
        """
        Estimate execution cost of a query step

        Args:
            step: Query step

        Returns:
            Estimated cost (higher = more expensive)
        """
        query = step.query
        base_cost = step.estimated_cost

        # Adjust based on query type
        if query.query_type == QueryType.VECTOR_SEARCH:
            # Vector search is expensive
            base_cost *= 2.0
        elif query.query_type == QueryType.PATH_FINDING:
            # Path finding is very expensive
            base_cost *= 3.0
        elif query.query_type == QueryType.TRAVERSAL:
            # Traversal cost depends on depth
            base_cost *= 1.0 + query.max_depth * 0.5

        # Adjust based on expected result size
        selectivity = self._estimate_selectivity(step)
        expected_results = selectivity * self.statistics.entity_count

        # More results = higher cost
        base_cost *= 1.0 + expected_results / 1000.0

        return base_cost

    def _get_dependency_levels(self, steps: List[QueryStep]) -> List[List[QueryStep]]:
        """
        Group steps by dependency level

        Args:
            steps: Query steps

        Returns:
            List of lists, where each inner list contains steps at the same dependency level
        """
        levels: List[List[QueryStep]] = []
        remaining = list(steps)
        completed: Set[str] = set()

        while remaining:
            # Find steps with all dependencies satisfied
            current_level = [step for step in remaining if all(dep in completed for dep in step.depends_on)]

            if not current_level:
                # Circular dependency or error
                logger.warning("Circular dependency detected in query plan")
                break

            levels.append(current_level)

            # Mark these steps as completed
            for step in current_level:
                completed.add(step.step_id)
                remaining.remove(step)

        return levels

    def _generate_explanation(
        self,
        original_plan: QueryPlan,
        optimized_plan: QueryPlan,
        rules_applied: List[str],
        cost_reduction: float,
    ) -> str:
        """
        Generate human-readable explanation of optimizations

        Args:
            original_plan: Original query plan
            optimized_plan: Optimized query plan
            rules_applied: List of rules applied
            cost_reduction: Estimated cost reduction

        Returns:
            Explanation string
        """
        parts = [
            f"Optimized query plan {original_plan.plan_id}:",
            f"- Original cost: {original_plan.total_estimated_cost:.3f}",
            f"- Optimized cost: {optimized_plan.total_estimated_cost:.3f}",
            f"- Cost reduction: {cost_reduction:.1%}",
            f"- Steps: {len(original_plan.steps)} -> {len(optimized_plan.steps)}",
        ]

        if rules_applied:
            parts.append(f"- Rules applied: {', '.join(rules_applied)}")

        return "\n".join(parts)

    def update_statistics(self, statistics: QueryStatistics) -> None:
        """
        Update query statistics

        Args:
            statistics: New query statistics
        """
        self.statistics = statistics
        logger.info(f"Updated query statistics: {statistics.entity_count} entities, {statistics.relation_count} relations")

    def get_optimization_count(self) -> int:
        """Get number of optimizations performed"""
        return self._optimization_count

    def __repr__(self) -> str:
        return f"QueryOptimizer(rules={len(self.enable_rules)}, optimizations={self._optimization_count})"


class QueryStatisticsCollector:
    """
    Collects query execution statistics for cost estimation

    Tracks:
    - Entity and relation counts
    - Entity/relation type distributions
    - Average node degree
    - Query execution times

    Example:
        ```python
        collector = QueryStatisticsCollector()

        # Collect from graph store
        stats = collector.collect_from_graph_store(graph_store)

        # Use for optimization
        optimizer = QueryOptimizer(statistics=stats)
        ```
    """

    def __init__(self) -> None:
        """Initialize statistics collector"""
        self._execution_times: List[float] = []

    def collect_from_graph_store(self, graph_store) -> QueryStatistics:
        """
        Collect statistics from a graph store

        Args:
            graph_store: Graph store instance

        Returns:
            Query statistics
        """
        from aiecs.infrastructure.graph_storage.base import GraphStore  # type: ignore[import-untyped]

        # Use duck typing to check if graph_store has required attributes
        # Some graph stores may not expose entities/relations directly
        if not hasattr(graph_store, 'entities') or not hasattr(graph_store, 'relations'):
            # Try to use isinstance check as fallback
            try:
                from aiecs.infrastructure.graph_storage.base import GraphStore as GS
                if not isinstance(graph_store, GS):
                    logger.debug("Graph store does not expose entities/relations attributes, skipping statistics collection")
                    return QueryStatistics()
            except Exception:
                logger.debug("Could not validate graph store type, skipping statistics collection")
                return QueryStatistics()

        # Count entities and relations
        try:
            entity_count = len(graph_store.entities)
            relation_count = len(graph_store.relations)
        except (AttributeError, TypeError):
            logger.debug("Graph store entities/relations not accessible, skipping statistics collection")
            return QueryStatistics()

        # Count by type
        entity_type_counts: Dict[str, int] = {}
        for entity in graph_store.entities.values():
            entity_type = entity.entity_type
            entity_type_counts[entity_type] = entity_type_counts.get(entity_type, 0) + 1

        relation_type_counts: Dict[str, int] = {}
        for relation in graph_store.relations.values():
            relation_type = relation.relation_type
            relation_type_counts[relation_type] = relation_type_counts.get(relation_type, 0) + 1

        # Calculate average degree by counting relations per entity
        # We count each relation for both source (outgoing) and target (incoming)
        outgoing_counts: Dict[str, int] = {}
        incoming_counts: Dict[str, int] = {}
        for relation in graph_store.relations.values():
            source_id = relation.source_id
            target_id = relation.target_id
            outgoing_counts[source_id] = outgoing_counts.get(source_id, 0) + 1
            incoming_counts[target_id] = incoming_counts.get(target_id, 0) + 1

        degree_sum = 0
        for entity_id in graph_store.entities:
            outgoing = outgoing_counts.get(entity_id, 0)
            incoming = incoming_counts.get(entity_id, 0)
            degree_sum += outgoing + incoming

        avg_degree = degree_sum / max(entity_count, 1)

        stats = QueryStatistics(
            entity_count=entity_count,
            relation_count=relation_count,
            avg_degree=avg_degree,
            entity_type_counts=entity_type_counts,
            relation_type_counts=relation_type_counts,
        )

        logger.info(f"Collected statistics: {entity_count} entities, {relation_count} relations, avg degree {avg_degree:.1f}")

        return stats

    def record_execution_time(self, execution_time_ms: float) -> None:
        """
        Record query execution time

        Args:
            execution_time_ms: Execution time in milliseconds
        """
        self._execution_times.append(execution_time_ms)

        # Keep only last 1000 executions
        if len(self._execution_times) > 1000:
            self._execution_times = self._execution_times[-1000:]

    def get_average_execution_time(self) -> float:
        """
        Get average query execution time

        Returns:
            Average execution time in milliseconds
        """
        if not self._execution_times:
            return 0.0
        return sum(self._execution_times) / len(self._execution_times)

    def get_execution_percentile(self, percentile: float) -> float:
        """
        Get execution time percentile

        Args:
            percentile: Percentile (0.0-1.0)

        Returns:
            Execution time at percentile
        """
        if not self._execution_times:
            return 0.0

        sorted_times = sorted(self._execution_times)
        index = int(len(sorted_times) * percentile)
        return sorted_times[min(index, len(sorted_times) - 1)]

    def reset(self) -> None:
        """Reset collected statistics"""
        self._execution_times = []
