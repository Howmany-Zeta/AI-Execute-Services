"""
Integration Tests for Logic Query Parser

Tests end-to-end integration with QueryPlanner and execution.

Phase: 2.4 - Logic Query Parser
Task: 4.1 - Integration with QueryPlanner
Version: 1.0
"""

import sys
from pathlib import Path
import asyncio
from unittest.mock import Mock

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from lark import Lark
    LARK_AVAILABLE = True
except ImportError:
    LARK_AVAILABLE = False
    print("Warning: lark-parser not installed. Skipping integration tests.")

if LARK_AVAILABLE:
    from aiecs.application.knowledge_graph.reasoning.logic_parser import LogicQueryParser
    from aiecs.application.knowledge_graph.reasoning.logic_query_integration import LogicQueryIntegration
    from aiecs.domain.knowledge_graph.models.query_plan import QueryPlan, QueryOperation

    # Import QueryPlanner only when needed to avoid circular import issues
    try:
        from aiecs.application.knowledge_graph.reasoning.query_planner import QueryPlanner
        QUERY_PLANNER_AVAILABLE = True
    except ImportError as e:
        QUERY_PLANNER_AVAILABLE = False
        QueryPlanner = None
        print(f"Warning: QueryPlanner not available: {e}")


# ============================================================================
# Mock Components
# ============================================================================

class MockGraphStore:
    """Mock graph store for testing"""
    def __init__(self):
        self.queries_executed = []
    
    async def execute_query(self, query):
        self.queries_executed.append(query)
        return {"entities": [], "count": 0}


class MockSchema:
    """Mock schema for testing"""
    def get_entity_type(self, type_name):
        return Mock(name=type_name)
    
    def list_entity_types(self):
        return ["Person", "Paper", "Company"]
    
    def get_relation_type(self, type_name):
        return Mock(name=type_name)
    
    def list_relation_types(self):
        return ["AuthoredBy", "WorksFor", "Knows"]


# ============================================================================
# Helper Functions
# ============================================================================

def skip_if_not_available(require_query_planner=False):
    """Check if required dependencies are available"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return True
    if require_query_planner and not QUERY_PLANNER_AVAILABLE:
        print("⊘ Skipping: QueryPlanner not available")
        return True
    return False


# ============================================================================
# Test Functions
# ============================================================================

def test_query_planner_logic_query_support():
    """Test QueryPlanner supports logic queries"""
    if skip_if_not_available(require_query_planner=True):
        return

    graph_store = MockGraphStore()
    schema = MockSchema()
    planner = QueryPlanner(graph_store, schema=schema)

    assert planner.supports_logic_queries(), "QueryPlanner should support logic queries"
    print("✓ QueryPlanner logic query support works")


def test_plan_logic_query_simple():
    """Test planning a simple logic query"""
    if skip_if_not_available(require_query_planner=True):
        return
    
    graph_store = MockGraphStore()
    schema = MockSchema()
    planner = QueryPlanner(graph_store, schema=schema)
    
    plan = planner.plan_logic_query("Find(Person)")
    
    assert isinstance(plan, QueryPlan), f"Expected QueryPlan, got {type(plan)}"
    assert len(plan.steps) == 1
    assert plan.steps[0].query.entity_type == "Person"
    print("✓ Simple logic query planning works")


def test_plan_logic_query_with_filter():
    """Test planning logic query with filter"""
    if skip_if_not_available():
        return
    
    graph_store = MockGraphStore()
    schema = MockSchema()
    planner = QueryPlanner(graph_store, schema=schema)
    
    plan = planner.plan_logic_query("Find(Person) WHERE age > 30")
    
    assert isinstance(plan, QueryPlan)
    assert len(plan.steps) == 1
    assert plan.steps[0].query.entity_type == "Person"
    assert "age" in plan.steps[0].query.properties
    print("✓ Logic query with filter planning works")


def test_plan_logic_query_with_traversal():
    """Test planning logic query with traversal"""
    if skip_if_not_available():
        return
    
    graph_store = MockGraphStore()
    schema = MockSchema()
    planner = QueryPlanner(graph_store, schema=schema)
    
    plan = planner.plan_logic_query("Find(Person) FOLLOWS AuthoredBy")
    
    assert isinstance(plan, QueryPlan)
    assert len(plan.steps) == 2
    assert plan.steps[0].query.entity_type == "Person"
    assert plan.steps[1].operation == QueryOperation.TRAVERSAL
    assert plan.steps[1].query.relation_type == "AuthoredBy"
    print("✓ Logic query with traversal planning works")


def test_plan_logic_query_multi_hop():
    """Test planning multi-hop logic query"""
    if skip_if_not_available():
        return
    
    graph_store = MockGraphStore()
    schema = MockSchema()
    planner = QueryPlanner(graph_store, schema=schema)
    
    plan = planner.plan_logic_query("Find(Person) FOLLOWS AuthoredBy FOLLOWS PublishedIn")
    
    assert isinstance(plan, QueryPlan)
    assert len(plan.steps) == 3
    assert plan.steps[0].query.entity_type == "Person"
    assert plan.steps[1].operation == QueryOperation.TRAVERSAL
    assert plan.steps[2].operation == QueryOperation.TRAVERSAL
    print("✓ Multi-hop logic query planning works")


def test_plan_logic_query_error_handling():
    """Test error handling in logic query planning"""
    if skip_if_not_available():
        return
    
    graph_store = MockGraphStore()
    schema = MockSchema()
    planner = QueryPlanner(graph_store, schema=schema)
    
    result = planner.plan_logic_query("Find(Person")  # Missing closing paren
    
    assert isinstance(result, list), "Expected error list"
    assert len(result) > 0
    assert hasattr(result[0], 'message')
    print("✓ Logic query error handling works")


async def test_integration_parse_and_execute():
    """Test LogicQueryIntegration parse_and_execute"""
    if skip_if_not_available():
        return

    graph_store = MockGraphStore()
    schema = MockSchema()
    integration = LogicQueryIntegration(graph_store, schema)

    result = await integration.parse_and_execute("Find(Person) WHERE age > 30")

    assert result["success"], f"Expected success, got {result}"
    assert "plan_id" in result
    assert "steps" in result
    assert len(result["steps"]) == 1
    print("✓ Integration parse_and_execute works")


async def test_integration_parse_and_execute_error():
    """Test LogicQueryIntegration error handling"""
    if skip_if_not_available():
        return

    graph_store = MockGraphStore()
    schema = MockSchema()
    integration = LogicQueryIntegration(graph_store, schema)

    result = await integration.parse_and_execute("Find(Person")  # Missing paren

    assert not result["success"]
    assert "errors" in result
    assert len(result["errors"]) > 0
    print("✓ Integration error handling works")


def test_integration_parse_to_query_plan():
    """Test LogicQueryIntegration parse_to_query_plan"""
    if skip_if_not_available():
        return

    graph_store = MockGraphStore()
    schema = MockSchema()
    integration = LogicQueryIntegration(graph_store, schema)

    plan = integration.parse_to_query_plan("Find(Person)")

    assert isinstance(plan, QueryPlan)
    assert len(plan.steps) == 1
    print("✓ Integration parse_to_query_plan works")


def test_query_plan_structure():
    """Test QueryPlan structure from logic query"""
    if skip_if_not_available():
        return

    graph_store = MockGraphStore()
    schema = MockSchema()
    planner = QueryPlanner(graph_store, schema=schema)

    plan = planner.plan_logic_query("Find(Person) WHERE age > 30 FOLLOWS AuthoredBy")

    assert isinstance(plan, QueryPlan)
    assert plan.plan_id is not None
    assert plan.original_query is not None
    assert len(plan.steps) == 2
    assert plan.total_estimated_cost > 0
    assert plan.explanation is not None
    print("✓ QueryPlan structure validation works")


def test_query_step_dependencies():
    """Test QueryStep dependencies are correct"""
    if skip_if_not_available():
        return

    graph_store = MockGraphStore()
    schema = MockSchema()
    planner = QueryPlanner(graph_store, schema=schema)

    plan = planner.plan_logic_query("Find(Person) FOLLOWS AuthoredBy FOLLOWS PublishedIn")

    assert len(plan.steps) == 3
    assert plan.steps[0].depends_on == []
    assert plan.steps[1].depends_on == ["step_1"]
    assert plan.steps[2].depends_on == ["step_2"]
    print("✓ QueryStep dependencies work")


def test_operator_conversion_in_plan():
    """Test operator conversion in QueryPlan"""
    if skip_if_not_available():
        return

    graph_store = MockGraphStore()
    schema = MockSchema()
    planner = QueryPlanner(graph_store, schema=schema)

    plan = planner.plan_logic_query("Find(Person) WHERE age > 30")

    properties = plan.steps[0].query.properties
    assert "age" in properties
    assert "$gt" in properties["age"]
    assert properties["age"]["$gt"] == 30
    print("✓ Operator conversion in plan works")


def test_in_operator_in_plan():
    """Test IN operator conversion in QueryPlan"""
    if skip_if_not_available():
        return

    graph_store = MockGraphStore()
    schema = MockSchema()
    planner = QueryPlanner(graph_store, schema=schema)

    plan = planner.plan_logic_query("Find(Person) WHERE status IN ['active', 'pending']")

    properties = plan.steps[0].query.properties
    assert "status" in properties
    assert "$in" in properties["status"]
    print("✓ IN operator in plan works")


def test_contains_operator_in_plan():
    """Test CONTAINS operator conversion in QueryPlan"""
    if skip_if_not_available():
        return

    graph_store = MockGraphStore()
    schema = MockSchema()
    planner = QueryPlanner(graph_store, schema=schema)

    plan = planner.plan_logic_query("Find(Paper) WHERE title CONTAINS 'machine learning'")

    properties = plan.steps[0].query.properties
    assert "title" in properties
    assert "$regex" in properties["title"]
    print("✓ CONTAINS operator in plan works")


def test_thread_safety_concurrent_parsing():
    """Test thread-safety with concurrent parsing"""
    if skip_if_not_available():
        return

    import threading

    graph_store = MockGraphStore()
    schema = MockSchema()
    planner = QueryPlanner(graph_store, schema=schema)

    results = []
    errors = []

    def parse_query(query_id):
        try:
            plan = planner.plan_logic_query(f"Find(Person) WHERE age > {query_id}")
            results.append((query_id, plan.plan_id))
        except Exception as e:
            errors.append((query_id, str(e)))

    # Create 10 threads parsing concurrently
    threads = []
    for i in range(10):
        t = threading.Thread(target=parse_query, args=(i,))
        threads.append(t)
        t.start()

    # Wait for all threads
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Errors occurred: {errors}"
    assert len(results) == 10
    # All plan IDs should be unique
    plan_ids = [r[1] for r in results]
    assert len(set(plan_ids)) == 10, "Plan IDs should be unique"
    print("✓ Thread-safety concurrent parsing works")


def test_query_results_match_expected():
    """Test query results structure matches expected format"""
    if skip_if_not_available():
        return

    graph_store = MockGraphStore()
    schema = MockSchema()
    planner = QueryPlanner(graph_store, schema=schema)

    plan = planner.plan_logic_query("Find(Person) WHERE age > 30")

    # Verify plan structure
    assert hasattr(plan, 'plan_id')
    assert hasattr(plan, 'original_query')
    assert hasattr(plan, 'steps')
    assert hasattr(plan, 'total_estimated_cost')
    assert hasattr(plan, 'explanation')

    # Verify step structure
    step = plan.steps[0]
    assert hasattr(step, 'step_id')
    assert hasattr(step, 'operation')
    assert hasattr(step, 'query')
    assert hasattr(step, 'description')
    assert hasattr(step, 'estimated_cost')
    print("✓ Query results structure validation works")


def run_all_tests():
    """Run all integration tests"""
    print("=" * 60)
    print("Logic Query Parser Integration Tests")
    print("=" * 60)
    print()

    if not LARK_AVAILABLE:
        print("⊘ lark-parser not installed. Install with: pip install lark-parser")
        return

    tests = [
        test_query_planner_logic_query_support,
        test_plan_logic_query_simple,
        test_plan_logic_query_with_filter,
        test_plan_logic_query_with_traversal,
        test_plan_logic_query_multi_hop,
        test_plan_logic_query_error_handling,
        test_integration_parse_to_query_plan,
        test_query_plan_structure,
        test_query_step_dependencies,
        test_operator_conversion_in_plan,
        test_in_operator_in_plan,
        test_contains_operator_in_plan,
        test_thread_safety_concurrent_parsing,
        test_query_results_match_expected,
    ]

    async_tests = [
        test_integration_parse_and_execute,
        test_integration_parse_and_execute_error,
    ]

    passed = 0
    failed = 0

    # Run synchronous tests
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1

    # Run async tests
    for test in async_tests:
        try:
            asyncio.run(test())
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()

