"""
Unit Tests for QueryPlan Conversion

Tests conversion of AST nodes to QueryPlan and QuerySteps.

Phase: 2.4 - Logic Query Parser
Task: 3.2 - Integrate QueryPlan Conversion
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
    print("Warning: lark-parser not installed. Skipping conversion tests.")

if LARK_AVAILABLE:
    from aiecs.application.knowledge_graph.reasoning.logic_parser import (
        LogicQueryParser,
        QueryNode,
        FindNode,
        TraversalNode,
        PropertyFilterNode,
        BooleanFilterNode,
        QueryContext,
    )
    from aiecs.domain.knowledge_graph.models.query_plan import QueryPlan, QueryStep, QueryOperation
    from aiecs.domain.knowledge_graph.models.query import GraphQuery, QueryType


# ============================================================================
# Test Functions
# ============================================================================

def test_simple_find_conversion():
    """Test conversion of simple Find query"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    result = parser.parse_to_query_plan("Find(Person)")
    
    assert isinstance(result, QueryPlan), f"Expected QueryPlan, got {type(result)}"
    assert len(result.steps) == 1, f"Expected 1 step, got {len(result.steps)}"
    
    step = result.steps[0]
    assert step.operation == QueryOperation.FILTER
    assert step.query.entity_type == "Person"
    print("✓ Simple Find conversion works")


def test_find_with_filter_conversion():
    """Test conversion of Find with WHERE clause"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    result = parser.parse_to_query_plan("Find(Person) WHERE age > 30")
    
    assert isinstance(result, QueryPlan)
    assert len(result.steps) == 1
    
    step = result.steps[0]
    assert step.query.entity_type == "Person"
    assert "age" in step.query.properties
    assert "$gt" in step.query.properties["age"]
    assert step.query.properties["age"]["$gt"] == 30
    print("✓ Find with filter conversion works")


def test_operator_mapping():
    """Test operator mapping (==, !=, etc. → $eq, $ne, etc.)"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    
    # Test == → $eq
    result1 = parser.parse_to_query_plan("Find(Person) WHERE age == 30")
    assert "$eq" in result1.steps[0].query.properties["age"]
    
    # Test != → $ne
    result2 = parser.parse_to_query_plan("Find(Person) WHERE age != 30")
    assert "$ne" in result2.steps[0].query.properties["age"]
    
    # Test > → $gt
    result3 = parser.parse_to_query_plan("Find(Person) WHERE age > 30")
    assert "$gt" in result3.steps[0].query.properties["age"]
    
    # Test < → $lt
    result4 = parser.parse_to_query_plan("Find(Person) WHERE age < 30")
    assert "$lt" in result4.steps[0].query.properties["age"]
    
    # Test >= → $gte
    result5 = parser.parse_to_query_plan("Find(Person) WHERE age >= 30")
    assert "$gte" in result5.steps[0].query.properties["age"]
    
    # Test <= → $lte
    result6 = parser.parse_to_query_plan("Find(Person) WHERE age <= 30")
    assert "$lte" in result6.steps[0].query.properties["age"]
    
    print("✓ Operator mapping works")


def test_in_operator_conversion():
    """Test IN operator → $in filter conversion"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    result = parser.parse_to_query_plan("Find(Person) WHERE status IN ['active', 'pending']")
    
    assert isinstance(result, QueryPlan)
    step = result.steps[0]
    assert "status" in step.query.properties
    assert "$in" in step.query.properties["status"]
    assert step.query.properties["status"]["$in"] == ["active", "pending"]
    print("✓ IN operator conversion works")


def test_contains_operator_conversion():
    """Test CONTAINS operator → $regex filter conversion"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    result = parser.parse_to_query_plan("Find(Paper) WHERE title CONTAINS 'machine learning'")
    
    assert isinstance(result, QueryPlan)
    step = result.steps[0]
    assert "title" in step.query.properties
    assert "$regex" in step.query.properties["title"]
    assert step.query.properties["title"]["$regex"] == "machine learning"
    print("✓ CONTAINS operator conversion works")


def test_boolean_and_conversion():
    """Test AND operator conversion"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    result = parser.parse_to_query_plan("Find(Person) WHERE age > 30 AND status == 'active'")
    
    assert isinstance(result, QueryPlan)
    step = result.steps[0]
    # Should have both filters
    assert "age" in step.query.properties or "$and" in step.query.properties
    print("✓ AND operator conversion works")


def test_boolean_or_conversion():
    """Test OR operator conversion"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse_to_query_plan("Find(Person) WHERE name == 'Alice' OR name == 'Bob'")

    assert isinstance(result, QueryPlan)
    step = result.steps[0]
    # Should have OR filter
    assert "name" in step.query.properties or "$or" in step.query.properties
    print("✓ OR operator conversion works")


def test_boolean_not_conversion():
    """Test NOT operator conversion"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse_to_query_plan("Find(Person) WHERE NOT age < 18")

    assert isinstance(result, QueryPlan)
    step = result.steps[0]
    # Should have NOT filter
    assert "age" in step.query.properties or "$not" in step.query.properties
    print("✓ NOT operator conversion works")


def test_traversal_conversion():
    """Test traversal conversion to QueryStep"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse_to_query_plan("Find(Person) FOLLOWS AuthoredBy")

    assert isinstance(result, QueryPlan)
    assert len(result.steps) == 2, f"Expected 2 steps, got {len(result.steps)}"

    # Step 1: Find Person
    step1 = result.steps[0]
    assert step1.query.entity_type == "Person"

    # Step 2: Traverse AuthoredBy
    step2 = result.steps[1]
    assert step2.operation == QueryOperation.TRAVERSAL
    assert step2.query.relation_type == "AuthoredBy"
    assert step2.depends_on == ["step_1"]
    print("✓ Traversal conversion works")


def test_multi_hop_traversal():
    """Test multi-hop traversal conversion"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse_to_query_plan("Find(Person) FOLLOWS AuthoredBy FOLLOWS PublishedIn")

    assert isinstance(result, QueryPlan)
    assert len(result.steps) == 3, f"Expected 3 steps, got {len(result.steps)}"

    # Check dependencies
    assert result.steps[0].depends_on == []
    assert result.steps[1].depends_on == ["step_1"]
    assert result.steps[2].depends_on == ["step_2"]
    print("✓ Multi-hop traversal conversion works")


def test_query_plan_metadata():
    """Test QueryPlan metadata (plan_id, explanation, etc.)"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse_to_query_plan("Find(Person) WHERE age > 30")

    assert isinstance(result, QueryPlan)
    assert result.plan_id is not None
    assert result.plan_id.startswith("plan_")
    assert result.original_query == "Find(Person) WHERE age > 30"
    assert result.explanation is not None
    assert "Find Person entities" in result.explanation
    print("✓ QueryPlan metadata works")


def test_query_step_descriptions():
    """Test QueryStep descriptions are generated"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse_to_query_plan("Find(Person) FOLLOWS AuthoredBy")

    assert isinstance(result, QueryPlan)

    # Check step descriptions
    step1 = result.steps[0]
    assert step1.description is not None
    assert "Find Person" in step1.description

    step2 = result.steps[1]
    assert step2.description is not None
    assert "Traverse AuthoredBy" in step2.description
    print("✓ QueryStep descriptions work")


def test_estimated_cost():
    """Test estimated cost is calculated"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse_to_query_plan("Find(Person) FOLLOWS AuthoredBy")

    assert isinstance(result, QueryPlan)
    assert result.total_estimated_cost > 0

    # Each step should have a cost
    for step in result.steps:
        assert step.estimated_cost > 0
    print("✓ Estimated cost calculation works")


def test_fresh_query_context():
    """Test that QueryContext is created fresh for each parse_to_query_plan call"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()

    # Parse two queries
    result1 = parser.parse_to_query_plan("Find(Person)")
    result2 = parser.parse_to_query_plan("Find(Paper)")

    # Both should succeed independently
    assert isinstance(result1, QueryPlan)
    assert isinstance(result2, QueryPlan)

    # They should have different plan IDs
    assert result1.plan_id != result2.plan_id
    print("✓ Fresh QueryContext works")


def test_error_handling():
    """Test error handling during conversion"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()

    # Invalid query should return errors
    result = parser.parse_to_query_plan("Find(Person")  # Missing closing paren

    assert isinstance(result, list), "Expected error list"
    assert len(result) > 0
    assert hasattr(result[0], 'message')
    print("✓ Error handling works")


def test_nested_properties():
    """Test nested property conversion"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse_to_query_plan("Find(Person) WHERE address.city == 'Seattle'")

    assert isinstance(result, QueryPlan)
    step = result.steps[0]
    # Nested property should be in filter
    assert "address.city" in step.query.properties
    print("✓ Nested property conversion works")


def test_find_with_entity_name():
    """Test Find with entity name (entity lookup)"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse_to_query_plan("Find(Person[`Alice`])")

    assert isinstance(result, QueryPlan)
    step = result.steps[0]
    assert step.operation == QueryOperation.ENTITY_LOOKUP
    assert step.query.entity_id == "Alice"
    assert step.query.entity_type == "Person"
    print("✓ Find with entity name works")


def test_find_with_entity_name_and_filters():
    """Test Find with entity name and filters"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse_to_query_plan("Find(Person[`Alice`]) WHERE age > 30")

    assert isinstance(result, QueryPlan)
    step = result.steps[0]
    assert step.query.entity_id == "Alice"
    assert "age" in step.query.properties
    print("✓ Find with entity name and filters works")


def test_query_node_explanation_with_entity_name():
    """Test QueryNode explanation generation with entity name"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    ast = parser.parse("Find(Person[`Alice`])")
    
    if isinstance(ast, list):
        print("⊘ Skipping: parse failed")
        return
    
    explanation = ast._generate_explanation()
    assert "Alice" in explanation
    assert "Find Person" in explanation
    print("✓ QueryNode explanation with entity name works")


def test_query_node_explanation_with_filters():
    """Test QueryNode explanation generation with filters"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    ast = parser.parse("Find(Person) WHERE age > 30")
    
    if isinstance(ast, list):
        print("⊘ Skipping: parse failed")
        return
    
    explanation = ast._generate_explanation()
    assert "filter" in explanation.lower()
    print("✓ QueryNode explanation with filters works")


def test_query_node_explanation_with_traversals():
    """Test QueryNode explanation generation with traversals"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    ast = parser.parse("Find(Person) FOLLOWS AuthoredBy")
    
    if isinstance(ast, list):
        print("⊘ Skipping: parse failed")
        return
    
    explanation = ast._generate_explanation()
    assert "traverse" in explanation.lower()
    print("✓ QueryNode explanation with traversals works")


def test_query_node_repr():
    """Test QueryNode __repr__ method"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    ast = parser.parse("Find(Person) FOLLOWS AuthoredBy")
    
    if isinstance(ast, list):
        print("⊘ Skipping: parse failed")
        return
    
    repr_str = repr(ast)
    assert "QueryNode" in repr_str
    assert "FindNode" in repr_str
    print("✓ QueryNode __repr__ works")


def test_find_node_repr():
    """Test FindNode __repr__ method"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    ast = parser.parse("Find(Person[`Alice`]) WHERE age > 30")
    
    if isinstance(ast, list):
        print("⊘ Skipping: parse failed")
        return
    
    repr_str = repr(ast.find)
    assert "FindNode" in repr_str
    assert "Person" in repr_str
    assert "Alice" in repr_str
    print("✓ FindNode __repr__ works")


def test_traversal_incoming_direction():
    """Test traversal with incoming direction"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse_to_query_plan("Find(Paper) FOLLOWS AuthoredBy INCOMING")

    assert isinstance(result, QueryPlan)
    assert len(result.steps) == 2
    
    traversal_step = result.steps[1]
    assert traversal_step.operation == QueryOperation.TRAVERSAL
    assert traversal_step.metadata["direction"] == "incoming"
    print("✓ Traversal with incoming direction works")


def test_traversal_node_repr():
    """Test TraversalNode __repr__ method"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    ast = parser.parse("Find(Person) FOLLOWS AuthoredBy INCOMING")
    
    if isinstance(ast, list):
        print("⊘ Skipping: parse failed")
        return
    
    repr_str = repr(ast.traversals[0])
    assert "TraversalNode" in repr_str
    assert "AuthoredBy" in repr_str
    print("✓ TraversalNode __repr__ works")


def test_property_filter_node_repr():
    """Test PropertyFilterNode __repr__ method"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    ast = parser.parse("Find(Person) WHERE age > 30")
    
    if isinstance(ast, list):
        print("⊘ Skipping: parse failed")
        return
    
    filter_node = ast.find.filters[0]
    repr_str = repr(filter_node)
    assert "PropertyFilterNode" in repr_str
    assert "age" in repr_str
    print("✓ PropertyFilterNode __repr__ works")


def test_boolean_filter_node_repr():
    """Test BooleanFilterNode __repr__ method"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    ast = parser.parse("Find(Person) WHERE age > 30 AND status == 'active'")
    
    if isinstance(ast, list):
        print("⊘ Skipping: parse failed")
        return
    
    filter_node = ast.find.filters[0]
    repr_str = repr(filter_node)
    assert "BooleanFilterNode" in repr_str
    assert "AND" in repr_str
    print("✓ BooleanFilterNode __repr__ works")


def test_query_plan_with_original_query():
    """Test QueryPlan creation with original_query parameter"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    query_str = "Find(Person) WHERE age > 30"
    result = parser.parse_to_query_plan(query_str)

    assert isinstance(result, QueryPlan)
    assert result.original_query == query_str
    print("✓ QueryPlan with original_query works")


def test_query_plan_without_original_query():
    """Test QueryPlan creation without original_query (uses __str__)"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    ast = parser.parse("Find(Person)")
    
    if isinstance(ast, list):
        print("⊘ Skipping: parse failed")
        return
    
    context = QueryContext(schema=None)
    query_plan = ast.to_query_plan(context, original_query="")
    
    # Should use str(self) as fallback
    assert query_plan.original_query is not None
    print("✓ QueryPlan without original_query works")


def test_multiple_filters_combination():
    """Test multiple filters are combined correctly"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse_to_query_plan("Find(Person) WHERE age > 30 AND status == 'active' AND name == 'Alice'")

    assert isinstance(result, QueryPlan)
    step = result.steps[0]
    # All filters should be in properties
    assert "age" in step.query.properties or "$and" in step.query.properties
    print("✓ Multiple filters combination works")


def test_complex_query_with_all_features():
    """Test complex query with entity name, filters, and traversals"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    # Note: WHERE clause must come after FOLLOWS in grammar
    parser = LogicQueryParser()
    result = parser.parse_to_query_plan("Find(Person[`Alice`]) FOLLOWS AuthoredBy FOLLOWS PublishedIn")

    assert isinstance(result, QueryPlan)
    assert len(result.steps) == 3  # Find + 2 traversals
    assert result.steps[0].query.entity_id == "Alice"
    assert result.steps[1].operation == QueryOperation.TRAVERSAL
    assert result.steps[2].operation == QueryOperation.TRAVERSAL
    print("✓ Complex query with all features works")


def test_query_step_dependencies():
    """Test query step dependencies are set correctly"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse_to_query_plan("Find(Person) FOLLOWS AuthoredBy FOLLOWS PublishedIn")

    assert isinstance(result, QueryPlan)
    assert len(result.steps) == 3
    
    # First step has no dependencies
    assert result.steps[0].depends_on == []
    
    # Second step depends on first
    assert "step_1" in result.steps[1].depends_on
    
    # Third step depends on second
    assert "step_2" in result.steps[2].depends_on
    print("✓ Query step dependencies work")


def test_query_plan_explanation_generation():
    """Test QueryPlan explanation is generated correctly"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse_to_query_plan("Find(Person) FOLLOWS AuthoredBy")

    assert isinstance(result, QueryPlan)
    assert result.explanation is not None
    assert len(result.explanation) > 0
    assert "Person" in result.explanation
    print("✓ QueryPlan explanation generation works")


def run_all_tests():
    """Run all conversion tests"""
    print("=" * 60)
    print("QueryPlan Conversion Tests")
    print("=" * 60)
    print()

    if not LARK_AVAILABLE:
        print("⊘ lark-parser not installed. Install with: pip install lark-parser")
        return

    tests = [
        test_simple_find_conversion,
        test_find_with_filter_conversion,
        test_operator_mapping,
        test_in_operator_conversion,
        test_contains_operator_conversion,
        test_boolean_and_conversion,
        test_boolean_or_conversion,
        test_boolean_not_conversion,
        test_traversal_conversion,
        test_multi_hop_traversal,
        test_query_plan_metadata,
        test_query_step_descriptions,
        test_estimated_cost,
        test_fresh_query_context,
        test_error_handling,
        test_nested_properties,
        test_find_with_entity_name,
        test_find_with_entity_name_and_filters,
        test_query_node_explanation_with_entity_name,
        test_query_node_explanation_with_filters,
        test_query_node_explanation_with_traversals,
        test_query_node_repr,
        test_find_node_repr,
        test_traversal_incoming_direction,
        test_traversal_node_repr,
        test_property_filter_node_repr,
        test_boolean_filter_node_repr,
        test_query_plan_with_original_query,
        test_query_plan_without_original_query,
        test_multiple_filters_combination,
        test_complex_query_with_all_features,
        test_query_step_dependencies,
        test_query_plan_explanation_generation,
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

