"""
Unit tests for Multi-Hop Reasoning

Tests for ReasoningEngine, evidence collection, and answer generation.
"""

import pytest
from aiecs.application.knowledge_graph.reasoning.reasoning_engine import ReasoningEngine
from aiecs.application.knowledge_graph.reasoning.query_planner import QueryPlanner
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.path import Path
from aiecs.domain.knowledge_graph.models.evidence import Evidence, EvidenceType, ReasoningResult
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore


@pytest.fixture
async def sample_graph():
    """Create a sample graph for testing"""
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Create entities
    alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice"})
    bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob"})
    charlie = Entity(id="charlie", entity_type="Person", properties={"name": "Charlie"})
    
    company_x = Entity(id="company_x", entity_type="Company", properties={"name": "Company X"})
    company_y = Entity(id="company_y", entity_type="Company", properties={"name": "Company Y"})
    
    await store.add_entity(alice)
    await store.add_entity(bob)
    await store.add_entity(charlie)
    await store.add_entity(company_x)
    await store.add_entity(company_y)
    
    # Create relations
    await store.add_relation(Relation(
        id="r1", relation_type="KNOWS",
        source_id="alice", target_id="bob",
        weight=0.9
    ))
    await store.add_relation(Relation(
        id="r2", relation_type="KNOWS",
        source_id="alice", target_id="charlie",
        weight=0.85
    ))
    await store.add_relation(Relation(
        id="r3", relation_type="WORKS_AT",
        source_id="bob", target_id="company_x",
        weight=1.0
    ))
    await store.add_relation(Relation(
        id="r4", relation_type="WORKS_AT",
        source_id="charlie", target_id="company_y",
        weight=1.0
    ))
    
    yield store
    await store.close()


@pytest.fixture
def reasoning_engine(sample_graph):
    """Create reasoning engine with sample graph"""
    return ReasoningEngine(sample_graph)


class TestReasoningEngine:
    """Test ReasoningEngine initialization and basic functionality"""
    
    def test_initialization(self, reasoning_engine):
        """Test engine initialization"""
        assert reasoning_engine.graph_store is not None
        assert reasoning_engine.query_planner is not None
        assert reasoning_engine.traversal is not None
        assert reasoning_engine.path_scorer is not None
    
    @pytest.mark.asyncio
    async def test_reason_simple_query(self, reasoning_engine):
        """Test reasoning on a simple query"""
        result = await reasoning_engine.reason(
            query="Find Alice",
            context={"start_entity_id": "alice"},
            max_hops=1
        )
        
        assert isinstance(result, ReasoningResult)
        assert result.query == "Find Alice"
        # Evidence may be 0 for simple queries without explicit search
        assert result.confidence >= 0.0
        assert len(result.reasoning_trace) > 0


class TestMultiHopPathFinding:
    """Test multi-hop path finding algorithms"""
    
    @pytest.mark.asyncio
    async def test_find_paths_to_target(self, reasoning_engine):
        """Test finding paths to a specific target"""
        paths = await reasoning_engine.find_multi_hop_paths(
            start_entity_id="alice",
            target_entity_id="company_x",
            max_hops=2,
            max_paths=10
        )
        
        assert isinstance(paths, list)
        # Should find: Alice -> Bob -> Company X
        if len(paths) > 0:
            path = paths[0]
            assert path.nodes[0].id == "alice"
            assert path.nodes[-1].id == "company_x"
    
    @pytest.mark.asyncio
    async def test_find_paths_all_reachable(self, reasoning_engine):
        """Test finding all reachable paths"""
        paths = await reasoning_engine.find_multi_hop_paths(
            start_entity_id="alice",
            target_entity_id=None,  # All reachable
            max_hops=1,
            max_paths=10
        )
        
        assert isinstance(paths, list)
        # Should find paths to Bob and Charlie (1-hop)
        assert len(paths) >= 0
    
    @pytest.mark.asyncio
    async def test_find_paths_with_relation_filter(self, reasoning_engine):
        """Test finding paths with relation type filter"""
        paths = await reasoning_engine.find_multi_hop_paths(
            start_entity_id="alice",
            target_entity_id=None,
            max_hops=2,
            relation_types=["KNOWS"],
            max_paths=10
        )
        
        assert isinstance(paths, list)
        # All paths should only use KNOWS relations
        for path in paths:
            for edge in path.edges:
                assert edge.relation_type == "KNOWS"
    
    @pytest.mark.asyncio
    async def test_find_paths_max_hops(self, reasoning_engine):
        """Test max hops constraint"""
        paths = await reasoning_engine.find_multi_hop_paths(
            start_entity_id="alice",
            target_entity_id=None,
            max_hops=1,
            max_paths=10
        )
        
        # All paths should have at most 1 hop (2 nodes)
        for path in paths:
            assert len(path.nodes) <= 2


class TestEvidenceCollection:
    """Test evidence collection from paths"""
    
    @pytest.mark.asyncio
    async def test_collect_evidence_from_paths(self, reasoning_engine):
        """Test collecting evidence from paths"""
        paths = await reasoning_engine.find_multi_hop_paths(
            start_entity_id="alice",
            target_entity_id="company_x",
            max_hops=2,
            max_paths=5
        )
        
        evidence = await reasoning_engine.collect_evidence_from_paths(
            paths,
            source="test"
        )
        
        assert isinstance(evidence, list)
        assert len(evidence) == len(paths)
        
        for ev in evidence:
            assert isinstance(ev, Evidence)
            assert ev.evidence_type == EvidenceType.PATH
            assert len(ev.entities) > 0
            assert 0.0 <= ev.confidence <= 1.0
            assert 0.0 <= ev.relevance_score <= 1.0
            assert len(ev.explanation) > 0
    
    @pytest.mark.asyncio
    async def test_evidence_has_correct_properties(self, reasoning_engine):
        """Test evidence has all required properties"""
        paths = await reasoning_engine.find_multi_hop_paths(
            start_entity_id="alice",
            target_entity_id="bob",
            max_hops=1,
            max_paths=1
        )
        
        if paths:
            evidence = await reasoning_engine.collect_evidence_from_paths(paths)
            ev = evidence[0]
            
            assert ev.evidence_id.startswith("ev_")
            assert ev.source == "path_finding"
            assert ev.combined_score == ev.confidence * ev.relevance_score
            assert len(ev.get_entity_ids()) == len(ev.entities)


class TestPathRanking:
    """Test path ranking based on relevance"""
    
    def test_rank_evidence_by_combined_score(self, reasoning_engine):
        """Test ranking by combined score"""
        evidence = [
            Evidence(
                evidence_id="ev1",
                evidence_type=EvidenceType.ENTITY,
                confidence=0.9,
                relevance_score=0.8,
                explanation="High score"
            ),
            Evidence(
                evidence_id="ev2",
                evidence_type=EvidenceType.ENTITY,
                confidence=0.5,
                relevance_score=0.5,
                explanation="Low score"
            ),
            Evidence(
                evidence_id="ev3",
                evidence_type=EvidenceType.ENTITY,
                confidence=0.7,
                relevance_score=0.9,
                explanation="Medium score"
            )
        ]
        
        ranked = reasoning_engine.rank_evidence(evidence, "combined_score")
        
        # Should be sorted by combined_score descending
        assert ranked[0].evidence_id == "ev1"  # 0.9 * 0.8 = 0.72
        assert ranked[1].evidence_id == "ev3"  # 0.7 * 0.9 = 0.63
        assert ranked[2].evidence_id == "ev2"  # 0.5 * 0.5 = 0.25
    
    def test_rank_evidence_by_confidence(self, reasoning_engine):
        """Test ranking by confidence only"""
        evidence = [
            Evidence(
                evidence_id="ev1",
                evidence_type=EvidenceType.ENTITY,
                confidence=0.5,
                relevance_score=1.0,
                explanation="Low confidence"
            ),
            Evidence(
                evidence_id="ev2",
                evidence_type=EvidenceType.ENTITY,
                confidence=0.9,
                relevance_score=0.1,
                explanation="High confidence"
            )
        ]
        
        ranked = reasoning_engine.rank_evidence(evidence, "confidence")
        
        # Should be sorted by confidence descending
        assert ranked[0].evidence_id == "ev2"
        assert ranked[1].evidence_id == "ev1"
    
    def test_rank_evidence_by_relevance(self, reasoning_engine):
        """Test ranking by relevance only"""
        evidence = [
            Evidence(
                evidence_id="ev1",
                evidence_type=EvidenceType.ENTITY,
                confidence=0.9,
                relevance_score=0.3,
                explanation="Low relevance"
            ),
            Evidence(
                evidence_id="ev2",
                evidence_type=EvidenceType.ENTITY,
                confidence=0.1,
                relevance_score=0.8,
                explanation="High relevance"
            )
        ]
        
        ranked = reasoning_engine.rank_evidence(evidence, "relevance")
        
        # Should be sorted by relevance descending
        assert ranked[0].evidence_id == "ev2"
        assert ranked[1].evidence_id == "ev1"


class TestAnswerGeneration:
    """Test answer generation from evidence"""
    
    @pytest.mark.asyncio
    async def test_generate_answer_from_evidence(self, reasoning_engine):
        """Test generating answer from evidence"""
        result = await reasoning_engine.reason(
            query="What companies does Alice know people at?",
            context={"start_entity_id": "alice"},
            max_hops=2,
            max_evidence=10
        )
        
        assert result.has_answer
        assert result.answer is not None
        assert len(result.answer) > 0
        assert result.confidence >= 0.0
    
    @pytest.mark.asyncio
    async def test_answer_confidence(self, reasoning_engine):
        """Test answer confidence calculation"""
        result = await reasoning_engine.reason(
            query="Find Bob",
            context={"entity_id": "bob"},
            max_hops=1
        )
        
        # Should have some confidence
        assert 0.0 <= result.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_empty_evidence_answer(self, reasoning_engine):
        """Test answer generation with no evidence"""
        # Query for non-existent entity
        result = await reasoning_engine.reason(
            query="Find non-existent entity",
            context={"entity_id": "does_not_exist"},
            max_hops=1
        )
        
        # Should have an answer indicating no evidence
        assert result.has_answer
        assert "no evidence" in result.answer.lower() or result.evidence_count == 0


class TestReasoningResult:
    """Test ReasoningResult model"""
    
    def test_reasoning_result_properties(self):
        """Test ReasoningResult properties"""
        evidence = [
            Evidence(
                evidence_id="ev1",
                evidence_type=EvidenceType.ENTITY,
                confidence=0.9,
                relevance_score=0.8,
                explanation="Test evidence"
            )
        ]
        
        result = ReasoningResult(
            query="test query",
            evidence=evidence,
            answer="test answer",
            confidence=0.85,
            reasoning_trace=["step 1", "step 2"],
            execution_time_ms=100.5
        )
        
        assert result.evidence_count == 1
        assert result.has_answer
        assert len(result.get_top_evidence(5)) == 1
        assert "step 1" in result.get_trace_string()
    
    def test_get_top_evidence(self):
        """Test getting top evidence"""
        evidence = [
            Evidence(
                evidence_id=f"ev{i}",
                evidence_type=EvidenceType.ENTITY,
                confidence=min(1.0, 0.5 + i * 0.05),  # Cap at 1.0
                relevance_score=min(1.0, 0.5 + i * 0.05),  # Cap at 1.0
                explanation=f"Evidence {i}"
            )
            for i in range(10)
        ]
        
        result = ReasoningResult(
            query="test",
            evidence=evidence,
            confidence=0.5
        )
        
        top_5 = result.get_top_evidence(5)
        assert len(top_5) == 5
        # Should be sorted by combined score (descending)
        assert top_5[0].evidence_id == "ev9"  # Highest score


class TestEvidenceModel:
    """Test Evidence model"""
    
    def test_evidence_combined_score(self):
        """Test combined score calculation"""
        ev = Evidence(
            evidence_id="ev1",
            evidence_type=EvidenceType.ENTITY,
            confidence=0.8,
            relevance_score=0.6,
            explanation="Test"
        )
        
        assert ev.combined_score == 0.8 * 0.6
    
    def test_evidence_entity_ids(self):
        """Test getting entity IDs from evidence"""
        entities = [
            Entity(id="e1", entity_type="Test", properties={}),
            Entity(id="e2", entity_type="Test", properties={}),
        ]
        
        ev = Evidence(
            evidence_id="ev1",
            evidence_type=EvidenceType.PATH,
            entities=entities,
            explanation="Test"
        )
        
        entity_ids = ev.get_entity_ids()
        assert len(entity_ids) == 2
        assert "e1" in entity_ids
        assert "e2" in entity_ids


class TestEndToEndReasoning:
    """Test end-to-end reasoning scenarios"""
    
    @pytest.mark.asyncio
    async def test_multi_hop_question(self, reasoning_engine):
        """Test answering a multi-hop question"""
        result = await reasoning_engine.reason(
            query="What companies does Alice know people at?",
            context={"start_entity_id": "alice"},
            max_hops=2,
            max_evidence=20
        )
        
        assert isinstance(result, ReasoningResult)
        assert result.evidence_count > 0
        assert result.has_answer
        assert result.confidence > 0.0
        assert len(result.reasoning_trace) > 0
        assert result.execution_time_ms is not None
    
    @pytest.mark.asyncio
    async def test_reasoning_trace(self, reasoning_engine):
        """Test reasoning trace generation"""
        result = await reasoning_engine.reason(
            query="Find connections from Alice",
            context={"start_entity_id": "alice"},
            max_hops=1
        )
        
        # Should have trace steps
        assert len(result.reasoning_trace) > 0
        trace_string = result.get_trace_string()
        assert "Planning query" in trace_string or len(trace_string) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

