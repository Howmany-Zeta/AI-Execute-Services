"""
Pattern Matching Tests

Tests for graph pattern matching engine.

Phase: 3.3 - Full Custom Query Execution
Version: 1.0
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, AsyncMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.path import Path as GraphPath
from aiecs.domain.knowledge_graph.models.path_pattern import PathPattern, TraversalDirection
from aiecs.application.knowledge_graph.pattern_matching import (
    PatternMatcher,
    PatternMatch
)


# ============================================================================
# Mock Graph Store
# ============================================================================

class MockGraphStore:
    """Mock graph store for testing"""
    
    def __init__(self):
        self.entities = {}
        self.relations = {}
    
    async def get_entity(self, entity_id: str):
        """Get entity by ID"""
        return self.entities.get(entity_id)
    
    async def traverse(
        self,
        start_entity_id: str,
        relation_type: str = None,
        max_depth: int = 3,
        max_results: int = 100
    ):
        """Mock traverse method"""
        # Return mock paths
        start_entity = self.entities.get(start_entity_id)
        if not start_entity:
            return []
        
        # Create simple mock path
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
    alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice", "age": 30})
    bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob", "age": 25})
    paper1 = Entity(id="paper1", entity_type="Paper", properties={"name": "ML Paper", "year": 2023})
    
    store.entities = {
        "alice": alice,
        "bob": bob,
        "paper1": paper1
    }
    
    # Create relations
    authored = Relation(
        id="rel1",
        relation_type="AuthoredBy",
        source_id="paper1",
        target_id="alice",
        properties={}
    )
    
    knows = Relation(
        id="rel2",
        relation_type="Knows",
        source_id="alice",
        target_id="bob",
        properties={}
    )
    
    store.relations = {
        "rel1": authored,
        "rel2": knows
    }
    
    return store


@pytest.fixture
def pattern_matcher(mock_graph_store):
    """Create pattern matcher with mock store"""
    return PatternMatcher(mock_graph_store)


# ============================================================================
# Pattern Matching Tests
# ============================================================================

@pytest.mark.asyncio
async def test_match_single_pattern(pattern_matcher, mock_graph_store):
    """Test matching a single pattern"""
    # Create pattern
    pattern = PathPattern(
        relation_types=["AuthoredBy"],
        max_depth=1
    )
    
    # Match pattern starting from paper1
    matches = await pattern_matcher.match_pattern(
        pattern,
        start_entity_id="paper1",
        max_matches=10
    )
    
    # Verify matches
    assert len(matches) > 0
    assert isinstance(matches[0], PatternMatch)
    assert len(matches[0].entities) == 2  # paper1 and alice
    assert len(matches[0].relations) == 1  # AuthoredBy relation


@pytest.mark.asyncio
async def test_match_pattern_with_entity_type_filter(pattern_matcher, mock_graph_store):
    """Test pattern matching with entity type filter"""
    # Create pattern with entity type constraint
    pattern = PathPattern(
        entity_types=["Person"],
        relation_types=["Knows"],
        max_depth=1
    )
    
    # Match pattern
    matches = await pattern_matcher.match_pattern(
        pattern,
        start_entity_id="alice",
        max_matches=10
    )
    
    # Verify matches
    assert len(matches) > 0
    # All entities should be Person type
    for match in matches:
        for entity in match.entities:
            assert entity.entity_type == "Person"


@pytest.mark.asyncio
async def test_match_multiple_patterns(pattern_matcher, mock_graph_store):
    """Test matching multiple patterns (AND semantics)"""
    # Create two patterns
    pattern1 = PathPattern(
        relation_types=["AuthoredBy"],
        max_depth=1
    )
    
    pattern2 = PathPattern(
        relation_types=["Knows"],
        max_depth=1
    )
    
    # Match both patterns
    matches = await pattern_matcher.match_multiple_patterns(
        [pattern1, pattern2],
        start_entity_id="paper1",
        max_matches=10
    )
    
    # Verify matches (should find paper1 -> alice -> bob)
    # Note: This depends on the mock implementation
    assert isinstance(matches, list)


@pytest.mark.asyncio
async def test_match_optional_patterns(pattern_matcher, mock_graph_store):
    """Test matching with optional patterns"""
    # Required pattern
    required = PathPattern(
        relation_types=["AuthoredBy"],
        max_depth=1
    )
    
    # Optional pattern
    optional = PathPattern(
        relation_types=["Knows"],
        max_depth=1
    )
    
    # Match with optional
    matches = await pattern_matcher.match_optional_patterns(
        required_patterns=[required],
        optional_patterns=[optional],
        start_entity_id="paper1",
        max_matches=10
    )
    
    # Verify matches
    assert isinstance(matches, list)
    # Should have matches even if optional doesn't match
    assert len(matches) > 0


@pytest.mark.asyncio
async def test_path_matches_pattern_with_cycles(pattern_matcher):
    """Test path matching with cycle detection"""
    # Create path with cycle
    alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice"})
    bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob"})
    
    rel1 = Relation(id="r1", relation_type="Knows", source_id="alice", target_id="bob", properties={})
    rel2 = Relation(id="r2", relation_type="Knows", source_id="bob", target_id="alice", properties={})
    
    path_with_cycle = GraphPath(
        nodes=[alice, bob, alice],  # Cycle: alice -> bob -> alice
        edges=[rel1, rel2]
    )
    
    # Pattern that disallows cycles
    pattern_no_cycles = PathPattern(
        relation_types=["Knows"],
        allow_cycles=False,
        max_depth=2
    )
    
    # Should not match
    assert not pattern_matcher._path_matches_pattern(path_with_cycle, pattern_no_cycles)
    
    # Pattern that allows cycles
    pattern_with_cycles = PathPattern(
        relation_types=["Knows"],
        allow_cycles=True,
        max_depth=2
    )
    
    # Should match
    assert pattern_matcher._path_matches_pattern(path_with_cycle, pattern_with_cycles)

