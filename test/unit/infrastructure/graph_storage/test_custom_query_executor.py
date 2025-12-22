"""
Custom Query Executor Tests

Tests for custom query execution with projection and aggregation.

Phase: 3.3 - Full Custom Query Execution
Version: 1.0
"""

import sys
from pathlib import Path
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from aiecs.domain.knowledge_graph.models.query import GraphQuery
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.path_pattern import PathPattern
from aiecs.application.knowledge_graph.pattern_matching import (
    CustomQueryExecutor,
    PatternMatch
)


# ============================================================================
# Mock Graph Store (reuse from pattern matching tests)
# ============================================================================

class MockGraphStore:
    """Mock graph store for testing"""
    
    def __init__(self):
        self.entities = {}
        self.relations = {}
    
    async def get_entity(self, entity_id: str):
        return self.entities.get(entity_id)
    
    async def traverse(self, start_entity_id: str, relation_type=None, max_depth=3, max_results=100):
        from aiecs.domain.knowledge_graph.models.path import Path as GraphPath
        
        start_entity = self.entities.get(start_entity_id)
        if not start_entity:
            return []
        
        paths = []
        for rel_id, relation in self.relations.items():
            if relation.source_id == start_entity_id:
                if relation_type is None or relation.relation_type == relation_type:
                    target_entity = self.entities.get(relation.target_id)
                    if target_entity:
                        path = GraphPath(
                            nodes=[start_entity, target_entity],
                            edges=[relation]
                        )
                        paths.append(path)
        
        return paths[:max_results]


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_graph_store():
    """Create mock graph store with test data"""
    store = MockGraphStore()

    # Create entities
    alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice", "age": 30, "city": "Seattle"})
    bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob", "age": 25, "city": "Seattle"})
    charlie = Entity(id="charlie", entity_type="Person", properties={"name": "Charlie", "age": 35, "city": "Portland"})
    
    store.entities = {
        "alice": alice,
        "bob": bob,
        "charlie": charlie
    }
    
    # Create relations
    knows1 = Relation(id="r1", relation_type="Knows", source_id="alice", target_id="bob", properties={})
    knows2 = Relation(id="r2", relation_type="Knows", source_id="alice", target_id="charlie", properties={})
    
    store.relations = {
        "r1": knows1,
        "r2": knows2
    }
    
    return store


@pytest.fixture
def query_executor(mock_graph_store):
    """Create query executor with mock store"""
    return CustomQueryExecutor(mock_graph_store)


# ============================================================================
# Projection Tests
# ============================================================================

@pytest.mark.asyncio
async def test_execute_query_with_projection(query_executor):
    """Test query execution with field projection"""
    # Create query with projection
    pattern = PathPattern(
        relation_types=["Knows"],
        max_depth=1
    )

    query = GraphQuery(
        query_type="custom",
        pattern=pattern,
        projection=["entities[0].properties.name", "entities[1].properties.name", "score"]
    )

    # Execute query
    result = await query_executor.execute(query, start_entity_id="alice")

    # Verify results
    assert "results" in result
    assert "matches" in result
    assert result["aggregated"] is False

    # Check projection
    if result["results"]:
        first_result = result["results"][0]
        assert "entities[0].properties.name" in first_result
        assert "entities[1].properties.name" in first_result
        assert "score" in first_result


@pytest.mark.asyncio
async def test_execute_query_with_nested_projection(query_executor):
    """Test query with nested field projection"""
    pattern = PathPattern(
        relation_types=["Knows"],
        max_depth=1
    )

    query = GraphQuery(
        query_type="custom",
        pattern=pattern,
        projection=["entities[0].properties.age", "entities[1].properties.city"]
    )

    result = await query_executor.execute(query, start_entity_id="alice")

    # Verify nested projection
    if result["results"]:
        first_result = result["results"][0]
        assert "entities[0].properties.age" in first_result
        assert "entities[1].properties.city" in first_result


# ============================================================================
# Aggregation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_execute_query_with_count_aggregation(query_executor):
    """Test query with COUNT aggregation"""
    pattern = PathPattern(
        relation_types=["Knows"],
        max_depth=1
    )

    query = GraphQuery(
        query_type="custom",
        pattern=pattern,
        aggregations={"total_count": "COUNT"}
    )

    result = await query_executor.execute(query, start_entity_id="alice")

    # Verify aggregation
    assert result["aggregated"] is True
    assert "results" in result
    assert len(result["results"]) == 1
    assert "total_count" in result["results"][0]
    assert isinstance(result["results"][0]["total_count"], int)


@pytest.mark.asyncio
async def test_field_extraction():
    """Test field extraction from pattern matches"""
    executor = CustomQueryExecutor(MockGraphStore())

    # Create test match
    alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice", "age": 30})
    bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob", "age": 25})
    rel = Relation(id="r1", relation_type="Knows", source_id="alice", target_id="bob", properties={})

    match = PatternMatch(
        entities=[alice, bob],
        relations=[rel],
        score=0.95
    )

    # Test various field extractions
    assert executor._extract_field(match, "score") == 0.95
    assert executor._extract_field(match, "entity_count") == 2
    assert executor._extract_field(match, "relation_count") == 1
    assert executor._extract_field(match, "entities[0].id") == "alice"
    assert executor._extract_field(match, "entities[1].id") == "bob"
    assert executor._extract_field(match, "entities[0].properties.age") == 30
    assert executor._extract_field(match, "relations[0].type") == "Knows"


@pytest.mark.asyncio
async def test_aggregation_functions():
    """Test aggregation function computation"""
    executor = CustomQueryExecutor(MockGraphStore())
    
    # Test data
    results = [
        {"age": 30, "city": "Seattle"},
        {"age": 25, "city": "Seattle"},
        {"age": 35, "city": "Portland"}
    ]
    
    # Test COUNT
    assert executor._compute_aggregation(results, "COUNT") == 3
    
    # Test SUM
    assert executor._compute_aggregation(results, "SUM(age)") == 90
    
    # Test AVG
    assert executor._compute_aggregation(results, "AVG(age)") == 30.0
    
    # Test MIN
    assert executor._compute_aggregation(results, "MIN(age)") == 25
    
    # Test MAX
    assert executor._compute_aggregation(results, "MAX(age)") == 35


@pytest.mark.asyncio
async def test_aggregation_with_grouping():
    """Test aggregation with GROUP BY"""
    executor = CustomQueryExecutor(MockGraphStore())
    
    # Test data
    results = [
        {"age": 30, "city": "Seattle"},
        {"age": 25, "city": "Seattle"},
        {"age": 35, "city": "Portland"}
    ]
    
    # Aggregate with grouping
    aggregated = executor._apply_aggregation(
        results,
        aggregations={"count": "COUNT", "avg_age": "AVG(age)"},
        group_by=["city"]
    )
    
    # Verify grouped results
    assert len(aggregated) == 2  # Two cities
    
    # Find Seattle group
    seattle_group = next((g for g in aggregated if g["city"] == "Seattle"), None)
    assert seattle_group is not None
    assert seattle_group["count"] == 2
    assert seattle_group["avg_age"] == 27.5
    
    # Find Portland group
    portland_group = next((g for g in aggregated if g["city"] == "Portland"), None)
    assert portland_group is not None
    assert portland_group["count"] == 1
    assert portland_group["avg_age"] == 35.0

