"""
Unit tests for Evidence Handling

Tests for Evidence models, synthesis, and confidence estimation.
"""

import pytest
from aiecs.domain.knowledge_graph.models.evidence import Evidence, EvidenceType, ReasoningResult
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.path import Path
from aiecs.application.knowledge_graph.reasoning.evidence_synthesis import EvidenceSynthesizer


class TestEvidenceModel:
    """Test Evidence model"""
    
    def test_create_evidence(self):
        """Test creating evidence"""
        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        
        evidence = Evidence(
            evidence_id="ev001",
            evidence_type=EvidenceType.ENTITY,
            entities=[entity],
            confidence=0.9,
            relevance_score=0.85,
            explanation="Test evidence",
            source="test"
        )
        
        assert evidence.evidence_id == "ev001"
        assert evidence.evidence_type == EvidenceType.ENTITY
        assert len(evidence.entities) == 1
        assert evidence.confidence == 0.9
        assert evidence.relevance_score == 0.85
    
    def test_combined_score(self):
        """Test combined score calculation"""
        evidence = Evidence(
            evidence_id="ev001",
            evidence_type=EvidenceType.ENTITY,
            confidence=0.8,
            relevance_score=0.7,
            explanation="Test"
        )
        
        assert evidence.combined_score == 0.8 * 0.7
    
    def test_get_entity_ids(self):
        """Test getting entity IDs"""
        entities = [
            Entity(id="e1", entity_type="Person", properties={}),
            Entity(id="e2", entity_type="Person", properties={})
        ]
        
        evidence = Evidence(
            evidence_id="ev001",
            evidence_type=EvidenceType.PATH,
            entities=entities,
            explanation="Test"
        )
        
        entity_ids = evidence.get_entity_ids()
        assert len(entity_ids) == 2
        assert "e1" in entity_ids
        assert "e2" in entity_ids


class TestReasoningResult:
    """Test ReasoningResult model"""
    
    def test_create_result(self):
        """Test creating reasoning result"""
        evidence = Evidence(
            evidence_id="ev001",
            evidence_type=EvidenceType.ENTITY,
            confidence=0.9,
            explanation="Test"
        )
        
        result = ReasoningResult(
            query="Test query",
            evidence=[evidence],
            answer="Test answer",
            confidence=0.85,
            reasoning_trace=["step 1", "step 2"]
        )
        
        assert result.query == "Test query"
        assert result.evidence_count == 1
        assert result.has_answer
        assert result.confidence == 0.85
    
    def test_get_top_evidence(self):
        """Test getting top evidence"""
        evidence_list = [
            Evidence(
                evidence_id=f"ev{i}",
                evidence_type=EvidenceType.ENTITY,
                confidence=0.5 + i * 0.1,
                relevance_score=0.5 + i * 0.1,
                explanation=f"Evidence {i}"
            )
            for i in range(5)
        ]
        
        result = ReasoningResult(
            query="test",
            evidence=evidence_list,
            confidence=0.7
        )
        
        top_3 = result.get_top_evidence(3)
        assert len(top_3) == 3
        # Should be sorted by combined score (descending)
        assert top_3[0].evidence_id == "ev4"


class TestEvidenceSynthesizer:
    """Test EvidenceSynthesizer"""
    
    def test_initialization(self):
        """Test synthesizer initialization"""
        synthesizer = EvidenceSynthesizer(
            confidence_threshold=0.6,
            contradiction_threshold=0.4
        )
        
        assert synthesizer.confidence_threshold == 0.6
        assert synthesizer.contradiction_threshold == 0.4
    
    def test_filter_by_confidence(self):
        """Test filtering by confidence"""
        synthesizer = EvidenceSynthesizer(confidence_threshold=0.7)
        
        evidence_list = [
            Evidence(
                evidence_id="ev1",
                evidence_type=EvidenceType.ENTITY,
                confidence=0.9,
                explanation="High confidence"
            ),
            Evidence(
                evidence_id="ev2",
                evidence_type=EvidenceType.ENTITY,
                confidence=0.5,
                explanation="Low confidence"
            ),
            Evidence(
                evidence_id="ev3",
                evidence_type=EvidenceType.ENTITY,
                confidence=0.8,
                explanation="Medium-high confidence"
            )
        ]
        
        filtered = synthesizer.filter_by_confidence(evidence_list)
        assert len(filtered) == 2
        assert all(ev.confidence >= 0.7 for ev in filtered)
    
    def test_synthesize_non_overlapping(self):
        """Test synthesizing non-overlapping evidence"""
        synthesizer = EvidenceSynthesizer()
        
        evidence_list = [
            Evidence(
                evidence_id="ev1",
                evidence_type=EvidenceType.ENTITY,
                entities=[Entity(id="e1", entity_type="Person", properties={})],
                confidence=0.9,
                explanation="Evidence 1"
            ),
            Evidence(
                evidence_id="ev2",
                evidence_type=EvidenceType.ENTITY,
                entities=[Entity(id="e2", entity_type="Person", properties={})],
                confidence=0.8,
                explanation="Evidence 2"
            )
        ]
        
        synthesized = synthesizer.synthesize_evidence(evidence_list)
        # Non-overlapping evidence should remain separate
        assert len(synthesized) == 2
    
    def test_synthesize_overlapping(self):
        """Test synthesizing overlapping evidence"""
        synthesizer = EvidenceSynthesizer()
        
        shared_entity = Entity(id="e1", entity_type="Person", properties={})
        
        evidence_list = [
            Evidence(
                evidence_id="ev1",
                evidence_type=EvidenceType.ENTITY,
                entities=[shared_entity],
                confidence=0.8,
                relevance_score=0.7,
                explanation="Evidence 1",
                source="source1"
            ),
            Evidence(
                evidence_id="ev2",
                evidence_type=EvidenceType.ENTITY,
                entities=[shared_entity],
                confidence=0.9,
                relevance_score=0.8,
                explanation="Evidence 2",
                source="source2"
            )
        ]
        
        synthesized = synthesizer.synthesize_evidence(evidence_list, method="weighted_average")
        
        # Should combine overlapping evidence
        assert len(synthesized) == 1
        combined = synthesized[0]
        
        # Confidence should be boosted by agreement
        assert combined.confidence >= 0.8
        assert combined.source == "synthesis"
        assert combined.metadata["source_count"] == 2
    
    def test_estimate_overall_confidence(self):
        """Test overall confidence estimation"""
        synthesizer = EvidenceSynthesizer()
        
        evidence_list = [
            Evidence(
                evidence_id="ev1",
                evidence_type=EvidenceType.ENTITY,
                confidence=0.8,
                source="source1",
                explanation="Test"
            ),
            Evidence(
                evidence_id="ev2",
                evidence_type=EvidenceType.ENTITY,
                confidence=0.9,
                source="source2",
                explanation="Test"
            ),
            Evidence(
                evidence_id="ev3",
                evidence_type=EvidenceType.ENTITY,
                confidence=0.85,
                source="source3",
                explanation="Test"
            )
        ]
        
        overall = synthesizer.estimate_overall_confidence(evidence_list)
        
        # Should be high due to multiple sources and good individual scores
        assert 0.8 <= overall <= 1.0
    
    def test_rank_by_reliability(self):
        """Test ranking by reliability"""
        synthesizer = EvidenceSynthesizer()
        
        evidence_list = [
            Evidence(
                evidence_id="ev1",
                evidence_type=EvidenceType.ENTITY,
                confidence=0.7,
                relevance_score=0.6,
                explanation="Low reliability"
            ),
            Evidence(
                evidence_id="ev2",
                evidence_type=EvidenceType.ENTITY,
                confidence=0.95,
                relevance_score=0.9,
                explanation="High reliability"
            ),
            Evidence(
                evidence_id="ev3",
                evidence_type=EvidenceType.ENTITY,
                confidence=0.85,
                relevance_score=0.8,
                explanation="Medium reliability"
            )
        ]
        
        ranked = synthesizer.rank_by_reliability(evidence_list)
        
        # Should be sorted by reliability
        assert ranked[0].evidence_id == "ev2"
        assert ranked[2].evidence_id == "ev1"
    
    def test_detect_contradictions(self):
        """Test contradiction detection"""
        synthesizer = EvidenceSynthesizer(contradiction_threshold=0.3)
        
        shared_entity = Entity(id="e1", entity_type="Person", properties={})
        
        evidence_list = [
            Evidence(
                evidence_id="ev1",
                evidence_type=EvidenceType.ENTITY,
                entities=[shared_entity],
                confidence=0.9,
                explanation="High confidence claim"
            ),
            Evidence(
                evidence_id="ev2",
                evidence_type=EvidenceType.ENTITY,
                entities=[shared_entity],
                confidence=0.3,
                explanation="Low confidence claim"
            )
        ]
        
        contradictions = synthesizer.detect_contradictions(evidence_list)
        
        # Should detect contradiction due to confidence difference
        assert len(contradictions) > 0
        assert contradictions[0]["entity_id"] == "e1"


class TestEvidenceSynthesisMethods:
    """Test different synthesis methods"""
    
    def test_weighted_average_method(self):
        """Test weighted average synthesis"""
        synthesizer = EvidenceSynthesizer()
        
        shared_entity = Entity(id="e1", entity_type="Person", properties={})
        
        evidence_list = [
            Evidence(
                evidence_id="ev1",
                evidence_type=EvidenceType.ENTITY,
                entities=[shared_entity],
                confidence=0.8,
                relevance_score=0.7,
                explanation="Ev 1"
            ),
            Evidence(
                evidence_id="ev2",
                evidence_type=EvidenceType.ENTITY,
                entities=[shared_entity],
                confidence=0.9,
                relevance_score=0.8,
                explanation="Ev 2"
            )
        ]
        
        synthesized = synthesizer.synthesize_evidence(evidence_list, method="weighted_average")
        assert len(synthesized) == 1
        
        # Should have agreement boost
        combined = synthesized[0]
        assert combined.confidence > 0.85
    
    def test_max_method(self):
        """Test max synthesis method"""
        synthesizer = EvidenceSynthesizer()
        
        shared_entity = Entity(id="e1", entity_type="Person", properties={})
        
        evidence_list = [
            Evidence(
                evidence_id="ev1",
                evidence_type=EvidenceType.ENTITY,
                entities=[shared_entity],
                confidence=0.7,
                relevance_score=0.6,
                explanation="Ev 1"
            ),
            Evidence(
                evidence_id="ev2",
                evidence_type=EvidenceType.ENTITY,
                entities=[shared_entity],
                confidence=0.9,
                relevance_score=0.8,
                explanation="Ev 2"
            )
        ]
        
        synthesized = synthesizer.synthesize_evidence(evidence_list, method="max")
        combined = synthesized[0]
        
        # Should take max values (plus agreement boost)
        assert combined.confidence >= 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

