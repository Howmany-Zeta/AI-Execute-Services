"""
Unit tests for graph traversal enhancements

Tests PathPattern, PathScorer, EnhancedTraversal, and cycle detection.
"""

import pytest
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.path import Path
from aiecs.domain.knowledge_graph.models.path_pattern import PathPattern, TraversalDirection
from aiecs.application.knowledge_graph.traversal.path_scorer import PathScorer
from aiecs.application.knowledge_graph.traversal.enhanced_traversal import EnhancedTraversal
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore


@pytest.fixture
async def simple_graph_store():
    """Fixture with a simple graph for testing"""
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Create entities: A -> B -> C -> D
    #                  A -> D (shortcut)
    a = Entity(id="a", entity_type="Person", properties={"name": "Alice"})
    b = Entity(id="b", entity_type="Company", properties={"name": "TechCorp"})
    c = Entity(id="c", entity_type="Location", properties={"name": "SF"})
    d = Entity(id="d", entity_type="Person", properties={"name": "Dave"})
    
    await store.add_entity(a)
    await store.add_entity(b)
    await store.add_entity(c)
    await store.add_entity(d)
    
    # Add relations
    await store.add_relation(Relation(
        id="r1", relation_type="WORKS_FOR", source_id="a", target_id="b", weight=1.0
    ))
    await store.add_relation(Relation(
        id="r2", relation_type="LOCATED_IN", source_id="b", target_id="c", weight=0.9
    ))
    await store.add_relation(Relation(
        id="r3", relation_type="LIVES_IN", source_id="c", target_id="d", weight=0.8
    ))
    await store.add_relation(Relation(
        id="r4", relation_type="KNOWS", source_id="a", target_id="d", weight=0.7
    ))
    
    yield store
    await store.close()


class TestPathPattern:
    """Test PathPattern domain model"""
    
    def test_basic_pattern_creation(self):
        """Test creating a basic path pattern"""
        pattern = PathPattern(
            relation_types=["WORKS_FOR", "LOCATED_IN"],
            max_depth=2
        )
        
        assert pattern.max_depth == 2
        assert "WORKS_FOR" in pattern.relation_types
        assert pattern.allow_cycles is False
    
    def test_pattern_relation_allowed(self):
        """Test checking if relation is allowed"""
        pattern = PathPattern(
            relation_types=["WORKS_FOR", "LOCATED_IN"],
            max_depth=2
        )
        
        assert pattern.is_relation_allowed("WORKS_FOR", 0) is True
        assert pattern.is_relation_allowed("KNOWS", 0) is False
    
    def test_pattern_required_sequence(self):
        """Test required relation sequence"""
        pattern = PathPattern(
            required_relation_sequence=["WORKS_FOR", "LOCATED_IN"],
            max_depth=2
        )
        
        # First relation must be WORKS_FOR
        assert pattern.is_relation_allowed("WORKS_FOR", 0) is True
        assert pattern.is_relation_allowed("LOCATED_IN", 0) is False
        
        # Second relation must be LOCATED_IN
        assert pattern.is_relation_allowed("LOCATED_IN", 1) is True
        assert pattern.is_relation_allowed("WORKS_FOR", 1) is False
    
    def test_pattern_entity_allowed(self):
        """Test checking if entity is allowed"""
        pattern = PathPattern(
            entity_types=["Person", "Company"],
            excluded_entity_ids={"e1"}
        )
        
        assert pattern.is_entity_allowed("e2", "Person") is True
        assert pattern.is_entity_allowed("e3", "Location") is False
        assert pattern.is_entity_allowed("e1", "Person") is False  # Excluded
    
    def test_pattern_valid_path_length(self):
        """Test path length validation"""
        pattern = PathPattern(
            min_path_length=2,
            max_depth=5
        )
        
        assert pattern.is_valid_path_length(1) is False
        assert pattern.is_valid_path_length(2) is True
        assert pattern.is_valid_path_length(5) is True
        assert pattern.is_valid_path_length(6) is False
    
    def test_pattern_should_continue_traversal(self):
        """Test traversal continuation check"""
        pattern = PathPattern(max_depth=3)
        
        assert pattern.should_continue_traversal(0) is True
        assert pattern.should_continue_traversal(2) is True
        assert pattern.should_continue_traversal(3) is False


class TestPathScorer:
    """Test path scoring and ranking"""
    
    @pytest.fixture
    def sample_paths(self):
        """Create sample paths for testing"""
        # Short path (length 1)
        p1 = Path(
            nodes=[
                Entity(id="a", entity_type="Person"),
                Entity(id="b", entity_type="Person")
            ],
            edges=[
                Relation(id="r1", relation_type="KNOWS", source_id="a", target_id="b", weight=0.9)
            ]
        )
        
        # Medium path (length 2)
        p2 = Path(
            nodes=[
                Entity(id="a", entity_type="Person"),
                Entity(id="b", entity_type="Person"),
                Entity(id="c", entity_type="Person")
            ],
            edges=[
                Relation(id="r1", relation_type="KNOWS", source_id="a", target_id="b", weight=0.8),
                Relation(id="r2", relation_type="WORKS_WITH", source_id="b", target_id="c", weight=0.7)
            ]
        )
        
        # Long path (length 3)
        p3 = Path(
            nodes=[
                Entity(id="a", entity_type="Person"),
                Entity(id="b", entity_type="Person"),
                Entity(id="c", entity_type="Person"),
                Entity(id="d", entity_type="Person")
            ],
            edges=[
                Relation(id="r1", relation_type="KNOWS", source_id="a", target_id="b", weight=0.6),
                Relation(id="r2", relation_type="KNOWS", source_id="b", target_id="c", weight=0.5),
                Relation(id="r3", relation_type="KNOWS", source_id="c", target_id="d", weight=0.4)
            ]
        )
        
        return [p1, p2, p3]
    
    def test_score_by_length_prefer_shorter(self, sample_paths):
        """Test scoring by length (prefer shorter)"""
        scorer = PathScorer()
        scored = scorer.score_by_length(sample_paths, prefer_shorter=True)
        
        # Shorter paths should have higher scores
        assert scored[0].score > scored[1].score
        assert scored[1].score > scored[2].score
    
    def test_score_by_length_prefer_longer(self, sample_paths):
        """Test scoring by length (prefer longer)"""
        scorer = PathScorer()
        scored = scorer.score_by_length(sample_paths, prefer_shorter=False)
        
        # Longer paths should have higher scores
        assert scored[2].score > scored[1].score
        assert scored[1].score > scored[0].score
    
    def test_score_by_weights(self, sample_paths):
        """Test scoring by relation weights"""
        scorer = PathScorer()
        scored = scorer.score_by_weights(sample_paths, aggregation="mean")
        
        # p1 has highest weight (0.9)
        # p2 has medium weights (0.8, 0.7 -> mean 0.75)
        # p3 has lowest weights (0.6, 0.5, 0.4 -> mean 0.5)
        assert scored[0].score > scored[1].score > scored[2].score
    
    def test_score_by_relation_types(self, sample_paths):
        """Test scoring by preferred relation types"""
        scorer = PathScorer()
        scored = scorer.score_by_relation_types(
            sample_paths,
            preferred_types=["KNOWS"],
            penalty=0.5
        )
        
        # p1: all KNOWS -> score 1.0
        # p2: 1 KNOWS, 1 WORKS_WITH -> score 0.75
        # p3: all KNOWS -> score 1.0
        assert scored[0].score == 1.0
        assert scored[2].score == 1.0
        assert scored[1].score < 1.0
    
    def test_score_custom(self, sample_paths):
        """Test custom scoring function"""
        scorer = PathScorer()
        
        # Score based on number of 'KNOWS' relations
        def count_knows(path: Path) -> float:
            knows_count = sum(1 for e in path.edges if e.relation_type == "KNOWS")
            return knows_count / max(len(path.edges), 1)
        
        scored = scorer.score_custom(sample_paths, count_knows)
        
        # p1: 1/1 KNOWS -> 1.0
        # p2: 1/2 KNOWS -> 0.5
        # p3: 3/3 KNOWS -> 1.0
        assert scored[0].score == 1.0
        assert scored[1].score == 0.5
        assert scored[2].score == 1.0
    
    def test_rank_paths(self, sample_paths):
        """Test ranking paths by score"""
        scorer = PathScorer()
        
        # Score by length first
        scored = scorer.score_by_length(sample_paths, prefer_shorter=True)
        
        # Rank top 2
        ranked = scorer.rank_paths(scored, top_k=2)
        
        assert len(ranked) == 2
        # Should be sorted by score descending
        assert ranked[0].score >= ranked[1].score
    
    def test_rank_paths_with_threshold(self, sample_paths):
        """Test ranking with minimum score threshold"""
        scorer = PathScorer()
        scored = scorer.score_by_length(sample_paths, prefer_shorter=True)
        
        # Only keep paths with score >= 0.5
        ranked = scorer.rank_paths(scored, min_score=0.5)
        
        # All returned paths should meet threshold
        for path in ranked:
            assert path.score >= 0.5


class TestCycleDetection:
    """Test cycle detection in paths"""
    
    def test_detect_no_cycle(self):
        """Test detecting paths without cycles"""
        path = Path(
            nodes=[
                Entity(id="a", entity_type="Person"),
                Entity(id="b", entity_type="Person"),
                Entity(id="c", entity_type="Person")
            ],
            edges=[
                Relation(id="r1", relation_type="KNOWS", source_id="a", target_id="b"),
                Relation(id="r2", relation_type="KNOWS", source_id="b", target_id="c")
            ]
        )
        
        traversal = EnhancedTraversal(None)  # No store needed for this test
        assert traversal.detect_cycles(path) is False
    
    def test_detect_cycle(self):
        """Test detecting paths with cycles"""
        entity_a = Entity(id="a", entity_type="Person")
        entity_b = Entity(id="b", entity_type="Person")
        
        # Create path that revisits 'a': a -> b -> a
        path = Path(
            nodes=[entity_a, entity_b, entity_a],
            edges=[
                Relation(id="r1", relation_type="KNOWS", source_id="a", target_id="b"),
                Relation(id="r2", relation_type="KNOWS", source_id="b", target_id="a")
            ]
        )
        
        traversal = EnhancedTraversal(None)
        assert traversal.detect_cycles(path) is True
    
    def test_filter_paths_without_cycles(self):
        """Test filtering out cyclic paths"""
        # Path without cycle
        p1 = Path(
            nodes=[
                Entity(id="a", entity_type="Person"),
                Entity(id="b", entity_type="Person")
            ],
            edges=[
                Relation(id="r1", relation_type="KNOWS", source_id="a", target_id="b")
            ]
        )
        
        # Path with cycle
        entity_a = Entity(id="a", entity_type="Person")
        p2 = Path(
            nodes=[entity_a, Entity(id="b", entity_type="Person"), entity_a],
            edges=[
                Relation(id="r1", relation_type="KNOWS", source_id="a", target_id="b"),
                Relation(id="r2", relation_type="KNOWS", source_id="b", target_id="a")
            ]
        )
        
        traversal = EnhancedTraversal(None)
        filtered = traversal.filter_paths_without_cycles([p1, p2])
        
        assert len(filtered) == 1
        assert filtered[0].start_entity.id == "a"
        assert filtered[0].end_entity.id == "b"


class TestEnhancedTraversal:
    """Test enhanced traversal with PathPattern"""
    
    @pytest.mark.asyncio
    async def test_traverse_with_simple_pattern(self, simple_graph_store):
        """Test traversal with a simple pattern"""
        traversal = EnhancedTraversal(simple_graph_store)
        
        pattern = PathPattern(
            max_depth=2,
            allow_cycles=False
        )
        
        paths = await traversal.traverse_with_pattern(
            start_entity_id="a",
            pattern=pattern,
            max_results=10
        )
        
        # Should find some paths
        assert len(paths) > 0
        
        # All paths should start with 'a'
        for path in paths:
            assert path.start_entity.id == "a"
    
    @pytest.mark.asyncio
    async def test_traverse_respects_max_depth(self, simple_graph_store):
        """Test that traversal respects max depth"""
        traversal = EnhancedTraversal(simple_graph_store)
        
        pattern = PathPattern(max_depth=1)
        
        paths = await traversal.traverse_with_pattern(
            start_entity_id="a",
            pattern=pattern,
            max_results=10
        )
        
        # All paths should have length <= 1
        for path in paths:
            assert path.length <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

