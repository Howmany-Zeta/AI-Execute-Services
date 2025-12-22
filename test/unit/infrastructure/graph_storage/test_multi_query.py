"""
Unit Tests for Multi-Query Support

Tests batch query parsing and execution.

Phase: 2.4 - Logic Query Parser
Task: 3.3 - Implement Multi-Query Support
Version: 1.0
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from lark import Lark
    LARK_AVAILABLE = True
except ImportError:
    LARK_AVAILABLE = False
    print("Warning: lark-parser not installed. Skipping multi-query tests.")

if LARK_AVAILABLE:
    from aiecs.application.knowledge_graph.reasoning.logic_parser import (
        LogicQueryParser,
        QueryNode,
        ParserError,
    )
    from aiecs.domain.knowledge_graph.models.query_plan import QueryPlan


# ============================================================================
# Test Functions
# ============================================================================

def test_parse_batch_basic():
    """Test basic batch parsing"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    queries = [
        "Find(Person)",
        "Find(Paper)"
    ]
    
    results = parser.parse_batch(queries)
    
    assert len(results) == 2, f"Expected 2 results, got {len(results)}"
    assert isinstance(results[0], QueryNode), f"Expected QueryNode, got {type(results[0])}"
    assert isinstance(results[1], QueryNode), f"Expected QueryNode, got {type(results[1])}"
    assert results[0].find.entity_type == "Person"
    assert results[1].find.entity_type == "Paper"
    print("✓ Basic batch parsing works")


def test_parse_batch_with_errors():
    """Test batch parsing with some errors"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    queries = [
        "Find(Person)",
        "Find(Paper",  # Missing closing paren
        "Find(Company)"
    ]
    
    results = parser.parse_batch(queries)
    
    assert len(results) == 3
    assert isinstance(results[0], QueryNode), "First query should succeed"
    assert isinstance(results[1], list), "Second query should fail"
    assert isinstance(results[2], QueryNode), "Third query should succeed"
    print("✓ Batch parsing with errors works")


def test_parse_batch_to_query_plans():
    """Test batch parsing to QueryPlans"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    queries = [
        "Find(Person) WHERE age > 30",
        "Find(Paper) WHERE year == 2023"
    ]
    
    plans = parser.parse_batch_to_query_plans(queries)
    
    assert len(plans) == 2
    assert isinstance(plans[0], QueryPlan), f"Expected QueryPlan, got {type(plans[0])}"
    assert isinstance(plans[1], QueryPlan), f"Expected QueryPlan, got {type(plans[1])}"
    assert plans[0].steps[0].query.entity_type == "Person"
    assert plans[1].steps[0].query.entity_type == "Paper"
    print("✓ Batch parsing to QueryPlans works")


def test_parse_batch_with_ids():
    """Test batch parsing with custom IDs"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    queries = {
        "find_people": "Find(Person) WHERE age > 30",
        "find_papers": "Find(Paper) WHERE year == 2023",
        "find_companies": "Find(Company)"
    }
    
    results = parser.parse_batch_with_ids(queries)
    
    assert len(results) == 3
    assert "find_people" in results
    assert "find_papers" in results
    assert "find_companies" in results
    assert isinstance(results["find_people"], QueryNode)
    assert isinstance(results["find_papers"], QueryNode)
    assert isinstance(results["find_companies"], QueryNode)
    print("✓ Batch parsing with IDs works")


def test_batch_independence():
    """Test that batch queries are independent"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    queries = [
        "Find(Person) WHERE age > 30",
        "Find(Paper) WHERE year == 2023"
    ]
    
    plans = parser.parse_batch_to_query_plans(queries)
    
    # Each query should have its own plan_id
    assert plans[0].plan_id != plans[1].plan_id
    
    # Each query should have independent steps
    assert plans[0].steps[0].step_id == "step_1"
    assert plans[1].steps[0].step_id == "step_1"  # Independent numbering
    print("✓ Batch query independence works")


def test_empty_batch():
    """Test empty batch"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    results = parser.parse_batch([])
    
    assert len(results) == 0
    print("✓ Empty batch works")


def test_batch_mixed_success_failure():
    """Test batch with mixed success and failure"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    queries = {
        "valid1": "Find(Person)",
        "invalid": "Find(",
        "valid2": "Find(Paper)"
    }

    results = parser.parse_batch_with_ids(queries)

    assert len(results) == 3
    assert isinstance(results["valid1"], QueryNode)
    assert isinstance(results["invalid"], list)  # Errors
    assert isinstance(results["valid2"], QueryNode)
    print("✓ Batch mixed success/failure works")


def run_all_tests():
    """Run all multi-query tests"""
    print("=" * 60)
    print("Multi-Query Support Tests")
    print("=" * 60)
    print()

    if not LARK_AVAILABLE:
        print("⊘ lark-parser not installed. Install with: pip install lark-parser")
        return

    tests = [
        test_parse_batch_basic,
        test_parse_batch_with_errors,
        test_parse_batch_to_query_plans,
        test_parse_batch_with_ids,
        test_batch_independence,
        test_empty_batch,
        test_batch_mixed_success_failure,
    ]

    passed = 0
    failed = 0

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

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()

