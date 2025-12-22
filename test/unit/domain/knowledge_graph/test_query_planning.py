"""
Unit tests for Query Planning

Tests for QueryPlanner, query decomposition, and optimization.
"""

import pytest
from aiecs.application.knowledge_graph.reasoning.query_planner import QueryPlanner
from aiecs.domain.knowledge_graph.models.query import GraphQuery, QueryType
from aiecs.domain.knowledge_graph.models.query_plan import (
    QueryPlan,
    QueryStep,
    QueryOperation,
    OptimizationStrategy
)
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore


@pytest.fixture
async def graph_store():
    """Create a graph store for testing"""
    store = InMemoryGraphStore()
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
def query_planner(graph_store):
    """Create query planner"""
    return QueryPlanner(graph_store)


class TestQueryPlanner:
    """Test QueryPlanner initialization and basic functionality"""
    
    def test_initialization(self, query_planner):
        """Test planner initialization"""
        assert query_planner.graph_store is not None
        assert len(query_planner.query_patterns) > 0
    
    def test_plan_simple_query(self, query_planner):
        """Test planning a simple query"""
        plan = query_planner.plan_query(
            "Find entities similar to machine learning",
            context={"query_embedding": [0.1] * 10}
        )
        
        assert isinstance(plan, QueryPlan)
        assert plan.plan_id.startswith("plan_")
        assert len(plan.steps) >= 1
        assert plan.original_query == "Find entities similar to machine learning"
        assert plan.total_estimated_cost > 0


class TestQueryDecomposition:
    """Test query decomposition into steps"""
    
    def test_vector_search_query(self, query_planner):
        """Test decomposition of vector search query"""
        plan = query_planner.plan_query(
            "Find papers similar to deep learning",
            context={
                "query_embedding": [0.1] * 128,
                "entity_type": "Paper"
            }
        )
        
        assert len(plan.steps) >= 1
        # Should have a vector search step
        has_vector_search = any(
            step.operation == QueryOperation.VECTOR_SEARCH
            for step in plan.steps
        )
        assert has_vector_search
    
    def test_relation_traversal_query(self, query_planner):
        """Test decomposition of relation traversal query"""
        plan = query_planner.plan_query(
            "Who works at Google",
            context={
                "entity_id": "company_google",
                "relation_type": "WORKS_AT"
            }
        )
        
        # Should have entity lookup + traversal
        assert len(plan.steps) >= 1
    
    def test_multi_hop_query(self, query_planner):
        """Test decomposition of multi-hop query"""
        plan = query_planner.plan_query(
            "What companies does Alice know people at",
            context={
                "start_entity_id": "person_alice",
                "num_hops": 2
            }
        )
        
        # Should have multiple steps for multi-hop
        assert len(plan.steps) >= 2
        
        # Check dependencies
        for i, step in enumerate(plan.steps[1:], 1):
            # Later steps should depend on earlier ones
            if i > 0:
                assert len(step.depends_on) > 0
    
    def test_path_finding_query(self, query_planner):
        """Test decomposition of path finding query"""
        plan = query_planner.plan_query(
            "Find path from Alice to Bob",
            context={
                "source_id": "person_alice",
                "target_id": "person_bob"
            }
        )
        
        assert len(plan.steps) >= 1
        # Should have path finding or traversal
        assert any(
            step.operation in [QueryOperation.TRAVERSAL]
            for step in plan.steps
        )
    
    def test_neighbor_query(self, query_planner):
        """Test decomposition of neighbor query"""
        plan = query_planner.plan_query(
            "Find neighbors of Alice",
            context={"entity_id": "person_alice"}
        )
        
        # Should have entity lookup + traversal
        assert len(plan.steps) >= 1


class TestQueryPlan:
    """Test QueryPlan model functionality"""
    
    def test_calculate_total_cost(self):
        """Test cost calculation"""
        steps = [
            QueryStep(
                step_id="step_1",
                operation=QueryOperation.ENTITY_LOOKUP,
                query=GraphQuery(query_type=QueryType.ENTITY_LOOKUP),
                description="Step 1",
                estimated_cost=0.2
            ),
            QueryStep(
                step_id="step_2",
                operation=QueryOperation.VECTOR_SEARCH,
                query=GraphQuery(query_type=QueryType.VECTOR_SEARCH),
                description="Step 2",
                estimated_cost=0.5
            )
        ]
        
        plan = QueryPlan(
            plan_id="plan_test",
            original_query="test query",
            steps=steps
        )
        
        total_cost = plan.calculate_total_cost()
        assert total_cost == 0.7
    
    def test_get_executable_steps(self):
        """Test getting executable steps"""
        steps = [
            QueryStep(
                step_id="step_1",
                operation=QueryOperation.ENTITY_LOOKUP,
                query=GraphQuery(query_type=QueryType.ENTITY_LOOKUP),
                description="Step 1",
                estimated_cost=0.2
            ),
            QueryStep(
                step_id="step_2",
                operation=QueryOperation.TRAVERSAL,
                query=GraphQuery(query_type=QueryType.TRAVERSAL),
                depends_on=["step_1"],
                description="Step 2",
                estimated_cost=0.4
            ),
            QueryStep(
                step_id="step_3",
                operation=QueryOperation.FILTER,
                query=GraphQuery(query_type=QueryType.CUSTOM),
                depends_on=["step_2"],
                description="Step 3",
                estimated_cost=0.3
            )
        ]
        
        plan = QueryPlan(
            plan_id="plan_test",
            original_query="test query",
            steps=steps
        )
        
        # Initially, only step_1 can execute
        executable = plan.get_executable_steps(set())
        assert len(executable) == 1
        assert executable[0].step_id == "step_1"
        
        # After step_1, step_2 can execute
        executable = plan.get_executable_steps({"step_1"})
        assert len(executable) == 1
        assert executable[0].step_id == "step_2"
        
        # After step_1 and step_2, step_3 can execute
        executable = plan.get_executable_steps({"step_1", "step_2"})
        assert len(executable) == 1
        assert executable[0].step_id == "step_3"
    
    def test_get_execution_order(self):
        """Test execution order calculation"""
        steps = [
            QueryStep(
                step_id="step_1",
                operation=QueryOperation.ENTITY_LOOKUP,
                query=GraphQuery(query_type=QueryType.ENTITY_LOOKUP),
                description="Step 1",
                estimated_cost=0.2
            ),
            QueryStep(
                step_id="step_2",
                operation=QueryOperation.VECTOR_SEARCH,
                query=GraphQuery(query_type=QueryType.VECTOR_SEARCH),
                description="Step 2 (parallel with step_1)",
                estimated_cost=0.4
            ),
            QueryStep(
                step_id="step_3",
                operation=QueryOperation.TRAVERSAL,
                query=GraphQuery(query_type=QueryType.TRAVERSAL),
                depends_on=["step_1"],
                description="Step 3 (after step_1)",
                estimated_cost=0.5
            ),
            QueryStep(
                step_id="step_4",
                operation=QueryOperation.RANK,
                query=GraphQuery(query_type=QueryType.CUSTOM),
                depends_on=["step_2", "step_3"],
                description="Step 4 (after step_2 and step_3)",
                estimated_cost=0.3
            )
        ]
        
        plan = QueryPlan(
            plan_id="plan_test",
            original_query="test query",
            steps=steps
        )
        
        execution_order = plan.get_execution_order()
        
        # Should have 3 levels
        # Level 0: step_1 and step_2 (no dependencies)
        # Level 1: step_3 (depends on step_1)
        # Level 2: step_4 (depends on step_2 and step_3)
        assert len(execution_order) >= 2
        
        # First level should have steps with no dependencies
        first_level = execution_order[0]
        assert "step_1" in first_level or "step_2" in first_level


class TestQueryOptimization:
    """Test query plan optimization"""
    
    def test_optimize_for_cost(self, query_planner):
        """Test cost optimization"""
        # Create a plan
        plan = query_planner.plan_query(
            "Find entities similar to AI and their connections",
            context={"query_embedding": [0.1] * 128}
        )
        
        # Optimize
        optimized = query_planner.optimize_plan(
            plan,
            strategy=OptimizationStrategy.MINIMIZE_COST
        )
        
        assert optimized.optimized is True
        assert len(optimized.steps) == len(plan.steps)
        assert optimized.plan_id.endswith("_opt")
    
    def test_optimize_for_latency(self, query_planner):
        """Test latency optimization"""
        plan = query_planner.plan_query(
            "Multi-step query",
            context={"num_hops": 2}
        )
        
        optimized = query_planner.optimize_plan(
            plan,
            strategy=OptimizationStrategy.MINIMIZE_LATENCY
        )
        
        assert optimized.optimized is True
    
    def test_optimize_balanced(self, query_planner):
        """Test balanced optimization"""
        plan = query_planner.plan_query(
            "Complex query",
            context={"query_embedding": [0.1] * 128}
        )
        
        optimized = query_planner.optimize_plan(
            plan,
            strategy=OptimizationStrategy.BALANCED
        )
        
        assert optimized.optimized is True
    
    def test_already_optimized_plan(self, query_planner):
        """Test optimizing an already optimized plan"""
        plan = query_planner.plan_query("test query")
        optimized = query_planner.optimize_plan(plan)
        
        # Try to optimize again
        twice_optimized = query_planner.optimize_plan(optimized)
        
        # Should return the same plan
        assert twice_optimized.plan_id == optimized.plan_id


class TestNaturalLanguageTranslation:
    """Test natural language to graph query translation"""
    
    def test_translate_vector_search(self, query_planner):
        """Test translation of vector search query"""
        query = query_planner.translate_to_graph_query(
            "Find similar entities",
            context={"query_embedding": [0.1] * 128}
        )
        
        assert query.query_type == QueryType.VECTOR_SEARCH
        assert query.embedding is not None
    
    def test_translate_path_finding(self, query_planner):
        """Test translation of path finding query"""
        query = query_planner.translate_to_graph_query(
            "Find path from A to B",
            context={"source_id": "a", "target_id": "b"}
        )
        
        assert query.query_type == QueryType.PATH_FINDING
        assert query.source_entity_id == "a"
        assert query.target_entity_id == "b"
    
    def test_translate_traversal(self, query_planner):
        """Test translation of traversal query"""
        query = query_planner.translate_to_graph_query(
            "Find neighbors of entity X",
            context={"entity_id": "x"}
        )
        
        assert query.query_type == QueryType.TRAVERSAL
        assert query.entity_id == "x"
    
    def test_translate_default_query(self, query_planner):
        """Test translation of generic query"""
        query = query_planner.translate_to_graph_query(
            "Find something",
            context={"entity_type": "Person"}
        )
        
        # Should default to entity lookup
        assert query.query_type == QueryType.ENTITY_LOOKUP


class TestQueryAnalysis:
    """Test query analysis functionality"""
    
    def test_analyze_multi_hop_query(self, query_planner):
        """Test analysis of multi-hop query"""
        query_info = query_planner._analyze_query(
            "Who works at companies that Alice knows people at"
        )
        
        assert query_info["is_multi_hop"] is True
        assert query_info["complexity"] in ["medium", "high"]
    
    def test_analyze_vector_search_query(self, query_planner):
        """Test analysis of vector search query"""
        query_info = query_planner._analyze_query(
            "Find papers similar to machine learning"
        )
        
        assert query_info["has_vector_search"] is True
    
    def test_analyze_path_finding_query(self, query_planner):
        """Test analysis of path finding query"""
        query_info = query_planner._analyze_query(
            "What is the path from Alice to Bob"
        )
        
        assert query_info["has_path_finding"] is True
    
    def test_complexity_estimation(self, query_planner):
        """Test complexity estimation"""
        simple_complexity = query_planner._estimate_complexity(
            "find alice"
        )
        assert simple_complexity in ["low", "medium"]
        
        complex_complexity = query_planner._estimate_complexity(
            "who works at companies that people who alice knows work at through connections"
        )
        assert complex_complexity in ["medium", "high"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

