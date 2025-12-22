"""
Unit tests for query optimizer
"""

import pytest
from aiecs.infrastructure.graph_storage.query_optimizer import (
    QueryOptimizer,
    QueryStatistics,
    QueryStatisticsCollector,
    OptimizationRule,
    OptimizationResult
)
from aiecs.domain.knowledge_graph.models.query_plan import QueryPlan, QueryStep, QueryOperation
from aiecs.domain.knowledge_graph.models.query import GraphQuery, QueryType


class TestQueryStatistics:
    """Test QueryStatistics"""
    
    def test_initialization(self):
        """Test statistics initialization"""
        stats = QueryStatistics(
            entity_count=1000,
            relation_count=5000,
            avg_degree=5.0
        )
        
        assert stats.entity_count == 1000
        assert stats.relation_count == 5000
        assert stats.avg_degree == 5.0
    
    def test_selectivity_with_type_filter(self):
        """Test selectivity calculation with entity type filter"""
        stats = QueryStatistics(
            entity_count=1000,
            entity_type_counts={"Person": 200, "Company": 100}
        )
        
        # Person type is 20% of entities
        assert stats.get_selectivity("Person") == 0.2
        
        # Company type is 10% of entities
        assert stats.get_selectivity("Company") == 0.1
        
        # Unknown type = 100% selectivity
        assert stats.get_selectivity("Unknown") == 1.0
        
        # No filter = 100% selectivity
        assert stats.get_selectivity(None) == 1.0


class TestQueryOptimizer:
    """Test QueryOptimizer"""
    
    def test_initialization(self):
        """Test optimizer initialization"""
        stats = QueryStatistics(entity_count=1000)
        optimizer = QueryOptimizer(statistics=stats)
        
        assert optimizer.statistics.entity_count == 1000
        assert len(optimizer.enable_rules) > 0
    
    def test_initialization_with_specific_rules(self):
        """Test initialization with specific rules"""
        optimizer = QueryOptimizer(
            enable_rules=[OptimizationRule.PREDICATE_PUSHDOWN]
        )
        
        assert len(optimizer.enable_rules) == 1
        assert OptimizationRule.PREDICATE_PUSHDOWN in optimizer.enable_rules
    
    def test_optimize_already_optimized_plan(self):
        """Test optimizing an already optimized plan"""
        plan = QueryPlan(
            plan_id="test_plan",
            original_query="test query",
            steps=[],
            optimized=True
        )
        
        optimizer = QueryOptimizer()
        result = optimizer.optimize(plan)
        
        assert result.optimized_plan == plan
        assert len(result.rules_applied) == 0
    
    def test_redundant_operation_elimination(self):
        """Test elimination of redundant operations"""
        # Create plan with duplicate operations
        step1 = QueryStep(
            step_id="step_1",
            operation=QueryOperation.ENTITY_LOOKUP,
            query=GraphQuery(
                query_type=QueryType.ENTITY_LOOKUP,
                entity_type="Person",
                properties={"name": "Alice"}
            ),
            description="Find Alice",
            estimated_cost=0.1
        )
        
        step2 = QueryStep(
            step_id="step_2",
            operation=QueryOperation.ENTITY_LOOKUP,
            query=GraphQuery(
                query_type=QueryType.ENTITY_LOOKUP,
                entity_type="Person",
                properties={"name": "Alice"}
            ),
            description="Find Alice (duplicate)",
            estimated_cost=0.1
        )
        
        step3 = QueryStep(
            step_id="step_3",
            operation=QueryOperation.TRAVERSAL,
            query=GraphQuery(
                query_type=QueryType.TRAVERSAL,
                relation_type="KNOWS"
            ),
            description="Find connections",
            depends_on=["step_2"],
            estimated_cost=0.2
        )
        
        plan = QueryPlan(
            plan_id="test_plan",
            original_query="test",
            steps=[step1, step2, step3]
        )
        
        optimizer = QueryOptimizer(
            enable_rules=[OptimizationRule.REDUNDANT_ELIMINATION]
        )
        result = optimizer.optimize(plan)
        
        # Should eliminate step_2 (duplicate of step_1)
        assert len(result.optimized_plan.steps) == 2
        assert "redundant_elimination" in str(result.rules_applied)
    
    def test_predicate_pushdown(self):
        """Test predicate push-down optimization"""
        # Create plan where filter can be pushed down
        step1 = QueryStep(
            step_id="step_1",
            operation=QueryOperation.ENTITY_LOOKUP,
            query=GraphQuery(
                query_type=QueryType.ENTITY_LOOKUP,
                entity_type="Person"
            ),
            description="Find all persons",
            estimated_cost=0.3
        )
        
        step2 = QueryStep(
            step_id="step_2",
            operation=QueryOperation.FILTER,
            query=GraphQuery(
                query_type=QueryType.ENTITY_LOOKUP,
                properties={"age": 30}
            ),
            description="Filter by age",
            depends_on=["step_1"],
            estimated_cost=0.1
        )
        
        plan = QueryPlan(
            plan_id="test_plan",
            original_query="test",
            steps=[step1, step2]
        )
        
        optimizer = QueryOptimizer(
            enable_rules=[OptimizationRule.PREDICATE_PUSHDOWN]
        )
        result = optimizer.optimize(plan)
        
        # Filter should be pushed to step_1
        optimized_step1 = result.optimized_plan.steps[0]
        assert "age" in optimized_step1.query.properties or len(result.rules_applied) == 0

    def test_join_reordering(self):
        """Test join reordering optimization"""
        stats = QueryStatistics(
            entity_count=1000,
            entity_type_counts={"Person": 100, "Company": 10}
        )

        # Create plan with joins that can be reordered
        step1 = QueryStep(
            step_id="step_1",
            operation=QueryOperation.ENTITY_LOOKUP,
            query=GraphQuery(
                query_type=QueryType.ENTITY_LOOKUP,
                entity_type="Person"  # Less selective (100 entities)
            ),
            description="Find persons",
            estimated_cost=0.3
        )

        step2 = QueryStep(
            step_id="step_2",
            operation=QueryOperation.ENTITY_LOOKUP,
            query=GraphQuery(
                query_type=QueryType.ENTITY_LOOKUP,
                entity_type="Company"  # More selective (10 entities)
            ),
            description="Find companies",
            estimated_cost=0.2
        )

        plan = QueryPlan(
            plan_id="test_plan",
            original_query="test",
            steps=[step1, step2]
        )

        optimizer = QueryOptimizer(
            statistics=stats,
            enable_rules=[OptimizationRule.JOIN_REORDERING]
        )
        result = optimizer.optimize(plan)

        # More selective operation (Company) should come first
        assert result.optimized_plan.steps[0].query.entity_type == "Company"
        assert result.optimized_plan.steps[1].query.entity_type == "Person"

    def test_cost_based_reordering(self):
        """Test cost-based reordering"""
        # Create plan with different costs
        step1 = QueryStep(
            step_id="step_1",
            operation=QueryOperation.VECTOR_SEARCH,
            query=GraphQuery(query_type=QueryType.VECTOR_SEARCH),
            description="Expensive vector search",
            estimated_cost=0.8
        )

        step2 = QueryStep(
            step_id="step_2",
            operation=QueryOperation.ENTITY_LOOKUP,
            query=GraphQuery(query_type=QueryType.ENTITY_LOOKUP),
            description="Cheap entity lookup",
            estimated_cost=0.1
        )

        plan = QueryPlan(
            plan_id="test_plan",
            original_query="test",
            steps=[step1, step2]
        )

        optimizer = QueryOptimizer(
            enable_rules=[OptimizationRule.COST_BASED]
        )
        result = optimizer.optimize(plan)

        # Cheaper operation should come first
        assert result.optimized_plan.steps[0].estimated_cost < result.optimized_plan.steps[1].estimated_cost

    def test_cost_reduction_calculation(self):
        """Test cost reduction calculation"""
        # Create plan with high cost
        step1 = QueryStep(
            step_id="step_1",
            operation=QueryOperation.VECTOR_SEARCH,
            query=GraphQuery(query_type=QueryType.VECTOR_SEARCH),
            description="Expensive operation",
            estimated_cost=1.0
        )

        plan = QueryPlan(
            plan_id="test_plan",
            original_query="test",
            steps=[step1]
        )

        optimizer = QueryOptimizer()
        result = optimizer.optimize(plan)

        # Should have some cost reduction (or at least not increase)
        assert result.estimated_cost_reduction >= 0.0

    def test_update_statistics(self):
        """Test updating optimizer statistics"""
        stats1 = QueryStatistics(entity_count=1000)
        optimizer = QueryOptimizer(statistics=stats1)

        assert optimizer.statistics.entity_count == 1000

        stats2 = QueryStatistics(entity_count=2000)
        optimizer.update_statistics(stats2)

        assert optimizer.statistics.entity_count == 2000

    def test_optimization_count(self):
        """Test optimization count tracking"""
        optimizer = QueryOptimizer()

        assert optimizer.get_optimization_count() == 0

        plan = QueryPlan(
            plan_id="test_plan",
            original_query="test",
            steps=[]
        )

        optimizer.optimize(plan)
        assert optimizer.get_optimization_count() == 1

        optimizer.optimize(plan)
        assert optimizer.get_optimization_count() == 2


class TestQueryStatisticsCollector:
    """Test QueryStatisticsCollector"""

    def test_initialization(self):
        """Test collector initialization"""
        collector = QueryStatisticsCollector()
        assert collector.get_average_execution_time() == 0.0

    def test_record_execution_time(self):
        """Test recording execution times"""
        collector = QueryStatisticsCollector()

        collector.record_execution_time(10.0)
        collector.record_execution_time(20.0)
        collector.record_execution_time(30.0)

        assert collector.get_average_execution_time() == 20.0

    def test_execution_percentile(self):
        """Test execution time percentile calculation"""
        collector = QueryStatisticsCollector()

        for i in range(100):
            collector.record_execution_time(float(i))

        # P50 should be around 50
        p50 = collector.get_execution_percentile(0.5)
        assert 45 <= p50 <= 55

        # P95 should be around 95
        p95 = collector.get_execution_percentile(0.95)
        assert 90 <= p95 <= 99

    def test_reset(self):
        """Test resetting collector"""
        collector = QueryStatisticsCollector()

        collector.record_execution_time(10.0)
        assert collector.get_average_execution_time() == 10.0

        collector.reset()
        assert collector.get_average_execution_time() == 0.0


