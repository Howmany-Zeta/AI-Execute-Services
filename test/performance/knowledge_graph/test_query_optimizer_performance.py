"""
Performance benchmarks for query optimizer
"""

import pytest
import time
from aiecs.infrastructure.graph_storage.query_optimizer import (
    QueryOptimizer,
    QueryStatistics,
    OptimizationRule
)
from aiecs.domain.knowledge_graph.models.query_plan import QueryPlan, QueryStep, QueryOperation
from aiecs.domain.knowledge_graph.models.query import GraphQuery, QueryType


@pytest.fixture
def complex_query_plan():
    """Create a complex query plan for testing"""
    steps = []
    
    # Create 10 steps with various operations
    for i in range(10):
        query_type = [
            QueryType.ENTITY_LOOKUP,
            QueryType.VECTOR_SEARCH,
            QueryType.TRAVERSAL
        ][i % 3]
        
        step = QueryStep(
            step_id=f"step_{i}",
            operation=QueryOperation.ENTITY_LOOKUP if query_type == QueryType.ENTITY_LOOKUP else QueryOperation.VECTOR_SEARCH,
            query=GraphQuery(
                query_type=query_type,
                entity_type=f"Type{i % 3}",
                properties={"field": f"value{i}"} if i % 2 == 0 else {},
                max_results=10
            ),
            description=f"Step {i}",
            depends_on=[f"step_{i-1}"] if i > 0 else [],
            estimated_cost=0.1 * (i + 1)
        )
        steps.append(step)
    
    return QueryPlan(
        plan_id="complex_plan",
        original_query="Complex multi-step query",
        steps=steps
    )


class TestQueryOptimizerPerformance:
    """Performance benchmarks for query optimizer"""
    
    def test_optimization_time(self, complex_query_plan):
        """Test optimization time for complex queries"""
        stats = QueryStatistics(
            entity_count=10000,
            relation_count=50000,
            entity_type_counts={"Type0": 3000, "Type1": 4000, "Type2": 3000}
        )
        
        optimizer = QueryOptimizer(statistics=stats)
        
        # Measure optimization time
        start_time = time.time()
        result = optimizer.optimize(complex_query_plan)
        optimization_time = (time.time() - start_time) * 1000  # Convert to ms
        
        print(f"\n=== Optimization Performance ===")
        print(f"Plan steps: {len(complex_query_plan.steps)}")
        print(f"Optimization time: {optimization_time:.2f}ms")
        print(f"Original cost: {complex_query_plan.total_estimated_cost:.3f}")
        print(f"Optimized cost: {result.optimized_plan.total_estimated_cost:.3f}")
        print(f"Cost reduction: {result.estimated_cost_reduction:.1%}")
        print(f"Rules applied: {result.rules_applied}")
        
        # Optimization should be fast (< 100ms for 10 steps)
        assert optimization_time < 100, f"Optimization too slow: {optimization_time:.2f}ms"
    
    def test_cost_reduction(self, complex_query_plan):
        """Test that optimization reduces query cost"""
        stats = QueryStatistics(
            entity_count=10000,
            entity_type_counts={"Type0": 1000, "Type1": 5000, "Type2": 4000}
        )
        
        optimizer = QueryOptimizer(statistics=stats)
        result = optimizer.optimize(complex_query_plan)
        
        original_cost = complex_query_plan.total_estimated_cost
        optimized_cost = result.optimized_plan.total_estimated_cost
        
        print(f"\n=== Cost Reduction ===")
        print(f"Original cost: {original_cost:.3f}")
        print(f"Optimized cost: {optimized_cost:.3f}")
        print(f"Reduction: {result.estimated_cost_reduction:.1%}")
        
        # Optimized cost should not be higher than original
        assert optimized_cost <= original_cost * 1.1, "Optimization increased cost significantly"
    
    def test_redundant_elimination_performance(self):
        """Test performance of redundant operation elimination"""
        # Create plan with many duplicate operations
        steps = []
        for i in range(50):
            # Create 5 groups of 10 duplicate operations each
            group = i // 10
            step = QueryStep(
                step_id=f"step_{i}",
                operation=QueryOperation.ENTITY_LOOKUP,
                query=GraphQuery(
                    query_type=QueryType.ENTITY_LOOKUP,
                    entity_type=f"Type{group}",
                    properties={"id": f"value{group}"}
                ),
                description=f"Lookup {group}",
                estimated_cost=0.1
            )
            steps.append(step)
        
        plan = QueryPlan(
            plan_id="redundant_plan",
            original_query="Query with duplicates",
            steps=steps
        )
        
        optimizer = QueryOptimizer(
            enable_rules=[OptimizationRule.REDUNDANT_ELIMINATION]
        )
        
        start_time = time.time()
        result = optimizer.optimize(plan)
        optimization_time = (time.time() - start_time) * 1000
        
        print(f"\n=== Redundant Elimination Performance ===")
        print(f"Original steps: {len(plan.steps)}")
        print(f"Optimized steps: {len(result.optimized_plan.steps)}")
        print(f"Eliminated: {len(plan.steps) - len(result.optimized_plan.steps)}")
        print(f"Optimization time: {optimization_time:.2f}ms")
        
        # Should eliminate duplicates
        assert len(result.optimized_plan.steps) < len(plan.steps)
        
        # Should be fast even with 50 steps
        assert optimization_time < 200, f"Elimination too slow: {optimization_time:.2f}ms"
    
    def test_join_reordering_performance(self):
        """Test performance of join reordering"""
        stats = QueryStatistics(
            entity_count=10000,
            entity_type_counts={
                "VeryCommon": 8000,
                "Common": 1500,
                "Rare": 500
            }
        )
        
        # Create plan with joins in suboptimal order
        steps = []
        types = ["VeryCommon", "Common", "Rare", "VeryCommon", "Common"]
        
        for i, entity_type in enumerate(types):
            step = QueryStep(
                step_id=f"step_{i}",
                operation=QueryOperation.ENTITY_LOOKUP,
                query=GraphQuery(
                    query_type=QueryType.ENTITY_LOOKUP,
                    entity_type=entity_type
                ),
                description=f"Find {entity_type}",
                estimated_cost=0.2
            )
            steps.append(step)
        
        plan = QueryPlan(
            plan_id="join_plan",
            original_query="Multi-join query",
            steps=steps
        )
        
        optimizer = QueryOptimizer(
            statistics=stats,
            enable_rules=[OptimizationRule.JOIN_REORDERING]
        )
        
        start_time = time.time()
        result = optimizer.optimize(plan)
        optimization_time = (time.time() - start_time) * 1000
        
        print(f"\n=== Join Reordering Performance ===")
        print(f"Steps: {len(plan.steps)}")
        print(f"Optimization time: {optimization_time:.2f}ms")
        print(f"Original order: {[s.query.entity_type for s in plan.steps]}")
        print(f"Optimized order: {[s.query.entity_type for s in result.optimized_plan.steps]}")
        
        # Should be fast
        assert optimization_time < 100, f"Reordering too slow: {optimization_time:.2f}ms"
        
        # Most selective (Rare) should come first
        first_type = result.optimized_plan.steps[0].query.entity_type
        assert first_type == "Rare", f"Expected Rare first, got {first_type}"

    def test_scalability_with_large_plans(self):
        """Test optimizer scalability with large query plans"""
        # Create increasingly large plans and measure optimization time
        results = []

        for num_steps in [10, 20, 50, 100]:
            steps = []
            for i in range(num_steps):
                step = QueryStep(
                    step_id=f"step_{i}",
                    operation=QueryOperation.ENTITY_LOOKUP,
                    query=GraphQuery(
                        query_type=QueryType.ENTITY_LOOKUP,
                        entity_type=f"Type{i % 5}",
                        properties={"field": f"value{i}"} if i % 3 == 0 else {}
                    ),
                    description=f"Step {i}",
                    depends_on=[f"step_{i-1}"] if i > 0 and i % 5 != 0 else [],
                    estimated_cost=0.1
                )
                steps.append(step)

            plan = QueryPlan(
                plan_id=f"plan_{num_steps}",
                original_query=f"Query with {num_steps} steps",
                steps=steps
            )

            optimizer = QueryOptimizer()

            start_time = time.time()
            result = optimizer.optimize(plan)
            optimization_time = (time.time() - start_time) * 1000

            results.append({
                "steps": num_steps,
                "time_ms": optimization_time,
                "cost_reduction": result.estimated_cost_reduction
            })

        print(f"\n=== Scalability Test ===")
        for r in results:
            print(f"Steps: {r['steps']:3d} | Time: {r['time_ms']:6.2f}ms | Cost reduction: {r['cost_reduction']:5.1%}")

        # Optimization time should scale reasonably (< 500ms for 100 steps)
        assert results[-1]["time_ms"] < 500, f"Optimization too slow for 100 steps: {results[-1]['time_ms']:.2f}ms"

        # Should be roughly linear or better
        time_per_step_10 = results[0]["time_ms"] / results[0]["steps"]
        time_per_step_100 = results[-1]["time_ms"] / results[-1]["steps"]

        print(f"\nTime per step (10 steps): {time_per_step_10:.3f}ms")
        print(f"Time per step (100 steps): {time_per_step_100:.3f}ms")

        # Should not degrade significantly (allow 3x degradation)
        assert time_per_step_100 < time_per_step_10 * 3, "Optimization does not scale well"

    def test_multiple_optimizations(self):
        """Test performance of multiple sequential optimizations"""
        stats = QueryStatistics(entity_count=5000)
        optimizer = QueryOptimizer(statistics=stats)

        # Create a simple plan
        plan = QueryPlan(
            plan_id="test_plan",
            original_query="test",
            steps=[
                QueryStep(
                    step_id="step_1",
                    operation=QueryOperation.ENTITY_LOOKUP,
                    query=GraphQuery(query_type=QueryType.ENTITY_LOOKUP),
                    description="Step 1",
                    estimated_cost=0.2
                )
            ]
        )

        # Optimize 100 times
        start_time = time.time()
        for _ in range(100):
            # Create new plan each time (since optimized plans are skipped)
            fresh_plan = QueryPlan(
                plan_id="test_plan",
                original_query="test",
                steps=list(plan.steps)
            )
            optimizer.optimize(fresh_plan)

        total_time = (time.time() - start_time) * 1000
        avg_time = total_time / 100

        print(f"\n=== Multiple Optimizations ===")
        print(f"Total time (100 optimizations): {total_time:.2f}ms")
        print(f"Average time per optimization: {avg_time:.2f}ms")
        print(f"Optimizations performed: {optimizer.get_optimization_count()}")

        # Average should be very fast
        assert avg_time < 10, f"Average optimization too slow: {avg_time:.2f}ms"
        assert optimizer.get_optimization_count() == 100


