"""
Unit tests for Logical Inference

Tests for InferenceEngine, inference rules, and caching.
"""

import pytest
from aiecs.application.knowledge_graph.reasoning.inference_engine import (
    InferenceEngine,
    InferenceCache
)
from aiecs.domain.knowledge_graph.models.inference_rule import (
    InferenceRule,
    InferenceStep,
    InferenceResult,
    RuleType
)
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore


@pytest.fixture
async def sample_graph():
    """Create a sample graph for testing inference"""
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Create entities
    alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice"})
    bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob"})
    charlie = Entity(id="charlie", entity_type="Person", properties={"name": "Charlie"})
    david = Entity(id="david", entity_type="Person", properties={"name": "David"})
    
    await store.add_entity(alice)
    await store.add_entity(bob)
    await store.add_entity(charlie)
    await store.add_entity(david)
    
    # Create relations for transitive inference
    # Alice -> Bob -> Charlie -> David
    await store.add_relation(Relation(
        id="r1", relation_type="KNOWS",
        source_id="alice", target_id="bob",
        weight=0.9
    ))
    await store.add_relation(Relation(
        id="r2", relation_type="KNOWS",
        source_id="bob", target_id="charlie",
        weight=0.85
    ))
    await store.add_relation(Relation(
        id="r3", relation_type="KNOWS",
        source_id="charlie", target_id="david",
        weight=0.8
    ))
    
    # Create symmetric relation
    await store.add_relation(Relation(
        id="r4", relation_type="FRIEND_OF",
        source_id="alice", target_id="bob",
        weight=1.0
    ))
    
    yield store
    await store.close()


@pytest.fixture
def inference_engine(sample_graph):
    """Create inference engine with sample graph"""
    return InferenceEngine(sample_graph)


class TestInferenceRule:
    """Test InferenceRule model"""
    
    def test_create_transitive_rule(self):
        """Test creating a transitive rule"""
        rule = InferenceRule(
            rule_id="rule_transitive",
            rule_type=RuleType.TRANSITIVE,
            relation_type="KNOWS",
            description="Transitive closure for KNOWS",
            confidence_decay=0.1
        )
        
        assert rule.rule_id == "rule_transitive"
        assert rule.rule_type == RuleType.TRANSITIVE
        assert rule.relation_type == "KNOWS"
        assert rule.enabled is True
        assert rule.confidence_decay == 0.1
    
    def test_create_symmetric_rule(self):
        """Test creating a symmetric rule"""
        rule = InferenceRule(
            rule_id="rule_symmetric",
            rule_type=RuleType.SYMMETRIC,
            relation_type="FRIEND_OF",
            description="Symmetric friendship",
            confidence_decay=0.05
        )
        
        assert rule.rule_type == RuleType.SYMMETRIC
        assert rule.relation_type == "FRIEND_OF"
    
    def test_can_apply(self):
        """Test rule applicability check"""
        rule = InferenceRule(
            rule_id="rule_1",
            rule_type=RuleType.TRANSITIVE,
            relation_type="KNOWS"
        )
        
        rel_knows = Relation(
            id="r1", relation_type="KNOWS",
            source_id="a", target_id="b"
        )
        rel_works = Relation(
            id="r2", relation_type="WORKS_AT",
            source_id="a", target_id="c"
        )
        
        assert rule.can_apply(rel_knows) is True
        assert rule.can_apply(rel_works) is False
    
    def test_disabled_rule(self):
        """Test disabled rule"""
        rule = InferenceRule(
            rule_id="rule_disabled",
            rule_type=RuleType.TRANSITIVE,
            relation_type="KNOWS",
            enabled=False
        )
        
        rel = Relation(
            id="r1", relation_type="KNOWS",
            source_id="a", target_id="b"
        )
        
        assert rule.can_apply(rel) is False


class TestInferenceEngine:
    """Test InferenceEngine functionality"""
    
    def test_initialization(self, inference_engine):
        """Test engine initialization"""
        assert inference_engine.graph_store is not None
        assert inference_engine.cache is not None
        assert len(inference_engine.rules) == 0
    
    def test_add_rule(self, inference_engine):
        """Test adding rules"""
        rule = InferenceRule(
            rule_id="rule_1",
            rule_type=RuleType.TRANSITIVE,
            relation_type="KNOWS"
        )
        
        inference_engine.add_rule(rule)
        assert "rule_1" in inference_engine.rules
        assert inference_engine.rules["rule_1"] == rule
    
    def test_remove_rule(self, inference_engine):
        """Test removing rules"""
        rule = InferenceRule(
            rule_id="rule_1",
            rule_type=RuleType.TRANSITIVE,
            relation_type="KNOWS"
        )
        
        inference_engine.add_rule(rule)
        assert "rule_1" in inference_engine.rules
        
        inference_engine.remove_rule("rule_1")
        assert "rule_1" not in inference_engine.rules
    
    def test_get_rules(self, inference_engine):
        """Test getting rules"""
        rule1 = InferenceRule(
            rule_id="rule_1",
            rule_type=RuleType.TRANSITIVE,
            relation_type="KNOWS"
        )
        rule2 = InferenceRule(
            rule_id="rule_2",
            rule_type=RuleType.SYMMETRIC,
            relation_type="FRIEND_OF"
        )
        
        inference_engine.add_rule(rule1)
        inference_engine.add_rule(rule2)
        
        # Get all rules
        all_rules = inference_engine.get_rules()
        assert len(all_rules) == 2
        
        # Get rules by type
        knows_rules = inference_engine.get_rules("KNOWS")
        assert len(knows_rules) == 1
        assert knows_rules[0].rule_id == "rule_1"
    
    @pytest.mark.asyncio
    async def test_infer_no_rules(self, inference_engine):
        """Test inference with no rules"""
        result = await inference_engine.infer_relations(
            relation_type="KNOWS",
            max_steps=3
        )
        
        assert isinstance(result, InferenceResult)
        assert len(result.inferred_relations) == 0
        assert result.total_steps == 0
        assert "No inference rules" in result.explanation


class TestTransitiveInference:
    """Test transitive inference"""
    
    @pytest.mark.asyncio
    async def test_apply_transitive_rule(self, inference_engine):
        """Test applying transitive rule"""
        rule = InferenceRule(
            rule_id="rule_transitive",
            rule_type=RuleType.TRANSITIVE,
            relation_type="KNOWS",
            confidence_decay=0.1
        )
        
        inference_engine.add_rule(rule)
        
        # Create test relations
        relations = [
            Relation(id="r1", relation_type="KNOWS", source_id="a", target_id="b", weight=0.9),
            Relation(id="r2", relation_type="KNOWS", source_id="b", target_id="c", weight=0.85)
        ]
        
        visited = set()
        inferred = await inference_engine._apply_transitive_rule(rule, relations, visited)
        
        # Should infer a->c
        assert len(inferred) >= 1
        
        # Check first inferred relation
        if inferred:
            inferred_rel, step = inferred[0]
            assert inferred_rel.source_id == "a"
            assert inferred_rel.target_id == "c"
            assert inferred_rel.relation_type == "KNOWS"
            assert inferred_rel.properties.get("inferred") is True
            
            # Check inference step
            assert step.confidence > 0
            assert step.rule.rule_id == "rule_transitive"
            assert len(step.source_relations) == 2


class TestSymmetricInference:
    """Test symmetric inference"""
    
    @pytest.mark.asyncio
    async def test_apply_symmetric_rule(self, inference_engine):
        """Test applying symmetric rule"""
        rule = InferenceRule(
            rule_id="rule_symmetric",
            rule_type=RuleType.SYMMETRIC,
            relation_type="FRIEND_OF",
            confidence_decay=0.05
        )
        
        inference_engine.add_rule(rule)
        
        # Create test relations
        relations = [
            Relation(id="r1", relation_type="FRIEND_OF", source_id="a", target_id="b", weight=1.0)
        ]
        
        visited = set()
        inferred = await inference_engine._apply_symmetric_rule(rule, relations, visited)
        
        # Should infer b->a
        assert len(inferred) >= 1
        
        if inferred:
            inferred_rel, step = inferred[0]
            assert inferred_rel.source_id == "b"
            assert inferred_rel.target_id == "a"
            assert inferred_rel.relation_type == "FRIEND_OF"
            assert inferred_rel.properties.get("inferred") is True
            
            # Check inference step
            assert step.confidence > 0
            assert step.rule.rule_id == "rule_symmetric"
            assert len(step.source_relations) == 1


class TestInferenceCache:
    """Test InferenceCache functionality"""
    
    def test_cache_initialization(self):
        """Test cache initialization"""
        cache = InferenceCache(max_size=100, ttl_seconds=300)
        
        assert cache.max_size == 100
        assert cache.ttl_seconds == 300
        assert cache.get_stats()["size"] == 0
    
    def test_cache_put_get(self):
        """Test caching results"""
        cache = InferenceCache()
        
        result = InferenceResult(
            inferred_relations=[],
            inference_steps=[],
            total_steps=1,
            confidence=0.9
        )
        
        # Put in cache
        cache.put("KNOWS", result, source_id="alice")
        
        # Get from cache
        cached = cache.get("KNOWS", source_id="alice")
        assert cached is not None
        assert cached.confidence == 0.9
    
    def test_cache_miss(self):
        """Test cache miss"""
        cache = InferenceCache()
        
        cached = cache.get("KNOWS", source_id="alice")
        assert cached is None
    
    def test_cache_eviction(self):
        """Test LRU eviction"""
        cache = InferenceCache(max_size=2)
        
        result1 = InferenceResult(total_steps=1, confidence=0.9)
        result2 = InferenceResult(total_steps=2, confidence=0.8)
        result3 = InferenceResult(total_steps=3, confidence=0.7)
        
        cache.put("KNOWS", result1, source_id="a")
        cache.put("KNOWS", result2, source_id="b")
        
        # Cache is full
        assert cache.get_stats()["size"] == 2
        
        # Adding third should evict least recently used
        cache.put("KNOWS", result3, source_id="c")
        assert cache.get_stats()["size"] == 2
    
    def test_cache_clear(self):
        """Test clearing cache"""
        cache = InferenceCache()
        
        result = InferenceResult(total_steps=1, confidence=0.9)
        cache.put("KNOWS", result)
        
        assert cache.get_stats()["size"] == 1
        
        cache.clear()
        assert cache.get_stats()["size"] == 0


class TestExplainability:
    """Test inference explainability"""
    
    def test_inference_step_explanation(self):
        """Test inference step explanation"""
        rule = InferenceRule(
            rule_id="rule_1",
            rule_type=RuleType.TRANSITIVE,
            relation_type="KNOWS"
        )
        
        rel1 = Relation(id="r1", relation_type="KNOWS", source_id="a", target_id="b")
        rel2 = Relation(id="r2", relation_type="KNOWS", source_id="b", target_id="c")
        inferred_rel = Relation(id="r3", relation_type="KNOWS", source_id="a", target_id="c")
        
        step = InferenceStep(
            step_id="step_1",
            inferred_relation=inferred_rel,
            source_relations=[rel1, rel2],
            rule=rule,
            confidence=0.8,
            explanation="Transitive: a -> b -> c => a -> c"
        )
        
        assert "Transitive" in step.explanation
        assert step.confidence == 0.8
    
    def test_inference_result_explanation(self):
        """Test inference result explanation"""
        result = InferenceResult(
            inferred_relations=[],
            inference_steps=[],
            total_steps=3,
            confidence=0.85,
            explanation="Test explanation"
        )
        
        assert result.get_explanation_string() == "Test explanation"
    
    def test_get_inference_trace(self, inference_engine):
        """Test getting inference trace"""
        rule = InferenceRule(
            rule_id="rule_1",
            rule_type=RuleType.TRANSITIVE,
            relation_type="KNOWS"
        )
        
        rel1 = Relation(id="r1", relation_type="KNOWS", source_id="a", target_id="b")
        rel2 = Relation(id="r2", relation_type="KNOWS", source_id="b", target_id="c")
        inferred_rel = Relation(id="r3", relation_type="KNOWS", source_id="a", target_id="c")
        
        step = InferenceStep(
            step_id="step_1",
            inferred_relation=inferred_rel,
            source_relations=[rel1, rel2],
            rule=rule,
            confidence=0.8,
            explanation="Test step"
        )
        
        result = InferenceResult(
            inferred_relations=[inferred_rel],
            inference_steps=[step],
            total_steps=1
        )
        
        trace = inference_engine.get_inference_trace(result)
        assert len(trace) > 0
        assert "Inference trace" in trace[0]


class TestInferenceResult:
    """Test InferenceResult model"""
    
    def test_has_results(self):
        """Test has_results property"""
        result_empty = InferenceResult(
            inferred_relations=[],
            inference_steps=[]
        )
        assert result_empty.has_results is False
        
        result_with_data = InferenceResult(
            inferred_relations=[
                Relation(id="r1", relation_type="KNOWS", source_id="a", target_id="b")
            ],
            inference_steps=[]
        )
        assert result_with_data.has_results is True
    
    def test_get_step_explanations(self):
        """Test getting step explanations"""
        step1 = InferenceStep(
            step_id="s1",
            inferred_relation=Relation(id="r1", relation_type="KNOWS", source_id="a", target_id="b"),
            source_relations=[],
            rule=InferenceRule(rule_id="r", rule_type=RuleType.TRANSITIVE, relation_type="KNOWS"),
            confidence=0.9,
            explanation="Step 1"
        )
        step2 = InferenceStep(
            step_id="s2",
            inferred_relation=Relation(id="r2", relation_type="KNOWS", source_id="b", target_id="c"),
            source_relations=[],
            rule=InferenceRule(rule_id="r", rule_type=RuleType.TRANSITIVE, relation_type="KNOWS"),
            confidence=0.8,
            explanation="Step 2"
        )
        
        result = InferenceResult(
            inferred_relations=[],
            inference_steps=[step1, step2]
        )
        
        explanations = result.get_step_explanations()
        assert len(explanations) == 2
        assert "Step 1" in explanations
        assert "Step 2" in explanations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

